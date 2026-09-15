"""AI-сервис: отправка запросов к OpenRouter (бесплатный Qwen) с
fallback на локальную базу знаний при ошибке или отсутствии ключа.
"""

import asyncio
import sys
from typing import Any

import httpx
from django.conf import settings

from . import ai_local

AI_SYSTEM_PROMPT = (
    "Ты — ментор по языку Python в корпоративном чате 'JOIN WORK!'.\n"
    "Твоя специализация — Python: синтаксис, идиомы, стандартная библиотека, "
    "асинхронность, ООП, тестирование, производительность. Ты учишь и объясняешь "
    "подходы как наставник, даёшь примеры кода и разбираешь ошибки.\n"
    "Отвечай на вопросы по веб-фреймворкам Python: Django, Django REST "
    "Framework, FastAPI, Flask, а также по SQLAlchemy, Pydantic, pytest и другим "
    "популярным библиотекам. Помогай и по смежным темам: базы данных, SQL, Git, "
    "Docker, алгоритмы, паттерны, архитектура.\n"
    "Если вопрос не про разработку — вежливо сообщи, что ты ментор по Python "
    "и веб-фреймворкам, и предложи переформулировать.\n"
    "Отвечай как наставник: кратко, по делу, с примерами кода. Используй markdown: "
    "код — в блоках ```, списки — с '-'. Пиши на языке вопроса."
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

    resp = None
    try:
        async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            models = [settings.OPENROUTER_MODEL, "google/gemma-4-31b-it:free", "inclusionai/ling-3.0-flash-vl:free"]
            for model in models:
                payload["model"] = model
                for attempt in range(2):
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("choices"):
                            content = data["choices"][0]["message"]["content"]
                            return content.strip() if content else None
                        # 200, но без choices — обычно сообщение об ошибке/перегрузке
                        err = data.get("error", {}).get("message") or data
                        print(f"[AI] no choices ({model}, attempt {attempt + 1}): {str(err)[:160]}", file=sys.stderr)
                    else:
                        print(f"[AI] HTTP {resp.status_code} ({model}): {resp.text[:160]}", file=sys.stderr)
                    await asyncio.sleep(1.5)
        return None
    except Exception as exc:
        print(f"[AI] OpenRouter error: {type(exc).__name__}: {exc}", file=sys.stderr)
        if resp is not None:
            try:
                print(f"[AI] raw body: {resp.text[:200]}", file=sys.stderr)
            except Exception:  # noqa: S110
                pass
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
        "Я — твой ментор по Python, но пока не распознал вопрос "
        "(и внешний сервис ИИ сейчас недоступен).\n"
        "Уточни, например: 'как работают декораторы в Python?', "
        "'что такое yield?', 'как написать тест в pytest?'. "
        "Напиши `/help` для списка команд."
    )
