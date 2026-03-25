import asyncio
import logging
import json
import subprocess
from asyncio import to_thread as thread

from openai import OpenAI

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ContentType
from aiogram.enums import ChatAction
from aiogram.utils.chat_action import ChatActionSender

from config import BOT_TOKEN, SUPERADMIN_ID
from config import GPT_MODEL, GPT_KEY

from database import init_db, close_db, create_user
from database import get_users, set_user_role, get_user_role
from database import get_user_last_response_id, set_user_last_response_id

from miscellaneous import pre_parse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


client = OpenAI(api_key=GPT_KEY)


with open("welcome_message.txt", "r", encoding="utf-8") as f:
    welcome_message = f.read()

with open("main_prompt.txt", "r", encoding="utf-8") as f:
    main_prompt = f.read()


async def tool_called(data: list) -> bool:
    for item in data:
        if item.type == 'function_call':
            return True
    return False


tools = [
    {
        "type": "function",
        "name": "run_command",
        "description": "Run command in server's terminal",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string"}
            },
            "required": ["command"]
        },
    },
    {
        "type": "function",
        "name": "launch_app",
        "description": "Run command in server's terminal to launch a long-run processes",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string"}
            },
            "required": ["command"]
        }
    }
]


@dp.message(Command("start"))
async def start(message: Message, bot: Bot):

    user = message.from_user

    await create_user(
        user_id=user.id,
        username=user.username
    )
        
    try:
        await message.answer(welcome_message, parse_mode="MarkdownV2")
    except Exception as e:
        await message.answer(welcome_message + f"\n\nSEQUENCE INTERRUPTED: {e}")

    await bot.send_message(SUPERADMIN_ID, f"New user | ID {user.id} | USERNAME {user.username}")

    if user.id == SUPERADMIN_ID:
        await set_user_role(user.id, "CREATOR")


@dp.message(Command("setrole"))
async def set_role(message: Message, bot: Bot):
    user = message.from_user

    their_id = int(message.text.split()[1])
    new_role = message.text.split()[2]

    if new_role.upper() not in ["CREATOR", "ADMIN", "DEVELOPER", "USER", "GUEST"]:
        await message.answer("Misspelled role\n\nList of roles:\nCREATOR\nADMIN\nDEVELOPER\nUSER\nGUEST")
        return

    their_role = await get_user_role(their_id)

    role = await get_user_role(user.id)

    if role == "ADMIN":
        if their_role not in ["CREATOR", "ADMIN"] and\
            new_role != "CREATOR":
            await set_user_role(their_id, new_role)

            await message.answer("Role updated")
        else:
            await message.answer("You as ADMIN can not change ADMIN's or CREATOR's role and can not assign CREATOR")
    elif role == "CREATOR":
        await set_user_role(their_id, new_role)

        await message.answer("Role updated")
    else:
        await message.answer("Insufficient rights")


@dp.message(F.text)
async def echo_handler(message: Message, bot: Bot):

    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        user = message.from_user
        user_role = await get_user_role(user.id)
        last_response_id = await get_user_last_response_id(user.id)

        if not user_role:
            message.answer("Access to the Agent was not granted")
            return
        
        agent_input = []
        agent_input += [{"role": "user", "content": message.text}]
        agent_input += [{"role": "system", "content": f"User's role: {user_role}"}]
        
        instructions = main_prompt# if not last_response_id else None

        response = await thread(client.responses.create,
            model=GPT_MODEL,
            input=agent_input,
            previous_response_id=last_response_id,
            instructions=instructions,
            tools=tools
        )

        last_response_id = response.id

        text_to_send = await pre_parse(response.output_text) or "_Getting started..._"
        try:
            sent_message = await message.answer(text_to_send, parse_mode="MarkdownV2")
        except Exception as e:
            sent_message = await message.answer(text_to_send + f"\n\nSEQUENCE INTERRUPTED: {e}")
        
        while await tool_called(response.output):
            next_input = []

            for item in response.output:
                if item.type == 'function_call':
                    if item.name == 'run_command':
                        args = json.loads(item.arguments)

                        text_command = args["command"][:12]+"..." if len(args["command"]) > 15 else args["command"]
                        try:
                            await sent_message.edit_text(f"Executed command: `{await pre_parse(text_command)}`", parse_mode="MarkdownV2")
                        except Exception as e:
                            await sent_message.edit_text(f"Executed command: `{text_command}`" + f"\n\nSEQUENCE INTERRUPTED: {e}")

                        result = await thread(subprocess.run,
                            args["command"],
                            shell=True,
                            capture_output=True,
                            text=True
                        )

                        output_text = result.stdout + result.stderr

                        next_input += [{
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": output_text
                        }]

                    if item.name == "launch_app":
                        args = json.loads(item.arguments)

                        text_command = args["command"][:12]+"..." if len(args["command"]) > 15 else args["command"]
                        try:
                            await sent_message.edit_text(f"Launched app: `{await pre_parse(text_command)}`", parse_mode="MarkdownV2")
                        except Exception as e:
                            await sent_message.edit_text(f"Launched app: `{text_command}`" + f"\n\nSEQUENCE INTERRUPTED: {e}")

                        process = subprocess.Popen(
                            args["command"],
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            start_new_session=True
                        )

                        output_text = f"PID {process.pid}"

                        next_input += [{
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": output_text
                        }]

            response = await thread(client.responses.create,
                model=GPT_MODEL,
                previous_response_id=response.id,
                input=next_input,
                tools=tools
            )

            last_response_id = response.id

            text_to_send = await pre_parse(response.output_text) or "_Job finished..._"
            try:
                await sent_message.edit_text(text_to_send, parse_mode="MarkdownV2")
            except Exception as e:
                await sent_message.edit_text(text_to_send + f"\n\nSEQUENCE INTERRUPTED: {e}")
        
        await set_user_last_response_id(user.id, last_response_id)



async def main():

    logger.info("Starting bot...")
    try:
        await init_db()
        
        await bot.delete_webhook(drop_pending_updates=True)
        
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error occurred: {e}")
    finally:
        await close_db()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
