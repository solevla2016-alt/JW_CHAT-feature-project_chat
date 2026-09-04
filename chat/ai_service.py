"""AI-сервис: отправка запросов к OpenRouter (бесплатный Qwen) с
fallback на локальную базу знаний при ошибке или отсутствии ключа.
"""

from typing import Any

import httpx

from django.conf import settings

from . import ai_local

AI_SYSTEM_PROMPT = (
    "Ты — AI-ассистент по программированию в корпоративном чате 'JOIN WORK!'.\n"
    "Отвечай ТОЛЬКО на вопросы, касающиеся разработки программного обеспечения: "
    "языки программирования, фреймворки, алгоритмы, структуры данных, базы данных, "
    "Git, Docker, архитектура, паттерны проектирования.\n"
    "Если вопрос не про разработку — вежливо сообщи, что твоя специализация — "
    "разработка ПО, и предложи переформулировать.\n"
    "Отвечай кратко и по делу. Используй markdown: код — в блоках ```, "
    "списки — с '-'. Пиши на языке вопроса."
)


async def ask_openrouter(prompt: str, history: list[dict[str, Any]]) -> str | None:
    """Отправляет запрос в OpenRouter. Возвращает ответ или None при ошибке."""
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        return None

    messages: list[dict[str, str]] = [{"role": "system", "content": AI_SYSTEM_PROMPT}]

    for msg in history:
        role = "assistant" if msg.get("is_ai") else ("assistant" if msg.get("username") == settings.AI_ASSISTANT_USERNAME else "user")
        messages.append({"role": role, "content": msg.get("text", "")})

    messages.append({"role": "user", "content": prompt})

    url = f"{settings.OPENROUTER_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": 800,
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip() if content else None
    except Exception:
        return None


def build_history(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Подготавливает контекст для модели из сырых сообщений."""
    return [
        {
            "text": m.get("message", m.get("text", "")),
            "username": m.get("username", ""),
            "is_ai": m.get("is_ai", False),
        }
        for m in messages
    ]


async def get_ai_answer(prompt: str, history: list[dict[str, Any]]) -> str:
    """Возвращает ответ: сначала OpenRouter, при сбое — локальный бот."""
    # /help обрабатывается локально всегда
    normalized = prompt.strip().lower()
    if normalized.startswith("/help"):
        return ai_local.ai_help_text()

    # Попытка через OpenRouter
    online = await ask_openrouter(prompt, history)
    if online:
        return online

    # Fallback на локальную базу знаний
    local = ai_local.local_ai_answer(prompt, history)
    if local:
        return local

    return (
        "Я не смог распознать вопрос (и внешний сервис ИИ сейчас недоступен).\n"
        "Уточни, например: 'как работают замыкания в Python?', "
        "'что такое JOIN в SQL?', 'как создать ветку в Git?'. "
        "Напиши `/help` для списка команд."
    )
