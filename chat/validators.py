import json


def validate_message(text_data: str) -> tuple[str | None, str | None]:
    try:
        data = json.loads(text_data)
    except json.JSONDecodeError:
        return None, "Некорректный JSON"

    if not isinstance(data, dict):
        return None, "Сообщение должно быть JSON-объектом"

    message = data.get("message")
    if not isinstance(message, str):
        return None, "Поле message должно быть строкой"

    message = message.strip()
    if not message:
        return None, "Сообщение не может быть пустым"

    if len(message) > 2000:
        return None, "Сообщение не может быть длиннее 2000 символов"

    return message, None
