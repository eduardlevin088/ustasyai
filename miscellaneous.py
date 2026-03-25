async def pre_parse(text: str) -> str:

    text = (
        text.replace('_', '\_')
            .replace('*', '\*')
            .replace('[', '\[')
            .replace(']', '\]')
            .replace('(', '\(')
            .replace(')', '\)')
            .replace('~', '\~')
            .replace('`', '\`')
            .replace('>', '\>')
            .replace('#', '\#')
            .replace('+', '\+')
            .replace('-', '\-')
            .replace('=', '\=')
            .replace('|', '\|')
            .replace('{', '\{')
            .replace('}', '\}')
            .replace('.', '\.')
            .replace('!', '\!')
    )

    return text