import os
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPERADMIN_ID = int(os.getenv("SUPERADMIN_ID"))

DB_NAME = os.getenv("DB_NAME")

GPT_KEY = os.getenv("GPT_KEY")
GPT_MODEL = os.getenv("GPT_MODEL")

_admin_ids_raw = (os.getenv("ADMIN_IDS") or "").strip()
ADMIN_IDS = [
    int(x.strip())
    for x in _admin_ids_raw.split(",")
    if x.strip().isdigit()
]


STATIC_DIR = BASE_DIR / "static"
AGENT_PROMPT_MAIN_PATH = "main_prompt.txt"

DB_PATH = BASE_DIR / DB_NAME
