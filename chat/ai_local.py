"""Локальная база знаний AI-ассистента (без интернета и API).

Отвечает на вопросы о разработке ПО. Используется как fallback,
если OpenRouter недоступен или не задан ключ.
"""

import re
from typing import Any

# Каждая запись: (ключевые_слова, ответ)
_KNOWLEDGE: list[tuple[list[str], str]] = [
    # --- Python ---
    (
        ["python", "декоратор"],
        "Декоратор в Python — функция, которая оборачивает другую функцию и "
        "изменяет её поведение.\n\n"
        "```python\n"
        "def timer(func):\n"
        "    import time\n"
        "    def wrapper(*args, **kwargs):\n"
        "        start = time.time()\n"
        "        res = func(*args, **kwargs)\n"
        "        print(f'{(time.time()-start):.3f}s')\n"
        "        return res\n"
        "    return wrapper\n\n"
        "@timer\ndef work():\n"
        "    time.sleep(1)\n"
        "```\n\n"
        "Применяется для логирования, кэширования, проверки прав.",
    ),
    (
        ["python", "генератор", "generator", "yield", "send", "next"],
        "Генератор — функция с `yield`, которая выдаёт значения по одному, "
        "не храня весь список в памяти.\n\n"
        "```python\n"
        "def count(n):\n"
        "    i = 0\n"
        "    while i < n:\n"
        "        yield i\n"
        "        i += 1\n"
        "```\n\n"
        "Экономит память на больших данных. Для посимвольного чтения файлов, "
        "бесконечных последовательностей.",
    ),
    (
        ["python", "async", "await", "асинхрон"],
        "`async/await` в Python — конкурентное выполнение I/O-операций в одном потоке "
        "через event loop.\n\n"
        "```python\n"
        "import asyncio, aiohttp\n\n"
        "async def fetch(url):\n"
        "    async with aiohttp.ClientSession() as s:\n"
        "        async with s.get(url) as r:\n"
        "            return await r.text()\n\n"
        "async def main():\n"
        "    results = await asyncio.gather(*[fetch(u) for u in urls])\n"
        "```\n\n"
        "Подходит для сетевых/дисковых операций, НЕ ускоряет CPU-задачи.",
    ),
    (
        ["python", "класс", "oop", "объект", "наследован"],
        "OOP в Python: классы, наследование, инкапсуляция, полиморфизм.\n\n"
        "```python\n"
        "class Animal:\n"
        "    def __init__(self, name):\n"
        "        self.name = name\n"
        "    def speak(self):\n"
        "        raise NotImplementedError\n\n"
        "class Dog(Animal):\n"
        "    def speak(self):\n"
        "        return f'{self.name} says woof'\n"
        "```\n\n"
        "Приватные поля — с `_` (соглашение) или `__` (name mangling).",
    ),
    (
        ["python", "список", "list comprehension", "генерат", "лист"],
        "List comprehension — краткий способ построить список.\n\n"
        "```python\n"
        "squares = [x**2 for x in range(10) if x % 2 == 0]\n"
        "# [0, 4, 16, 36, 64]\n"
        "```\n\n"
        "Быстрее и читабельнее, чем `for` с `append`.",
    ),
    (
        ["python", "except", "исключен", "ошибка", "try"],
        "Обработка исключений в Python:\n\n"
        "```python\n"
        "try:\n"
        "    x = int(raw)\n"
        "except ValueError as e:\n"
        "    print('не число', e)\n"
        "except ZeroDivisionError:\n"
        "    print('/0')\n"
        "finally:\n"
        "    cleanup()\n"
        "```\n\n"
        "Не лови голый `except:` — лови конкретные типы.",
    ),
    (
        ["django", "orm", "queryset", "запрос", "база"],
        "Django ORM — работа с БД на Python, без SQL.\n\n"
        "```python\n"
        "# фильтрация\n"
        "users = User.objects.filter(age__gte=18, name__icontains='a')\n"
        "# связанные объекты (предзагрузка — без N+1)\n"
        "rooms = Room.objects.select_related('owner').prefetch_related('members')\n"
        "# агрегация\n"
        "from django.db.models import Count\n"
        "Room.objects.annotate(members_count=Count('members'))\n"
        "```",
    ),
    (
        ["django", "миграция", "migrate"],
        "Миграции в Django — версионирование схемы БД.\n\n"
        "```bash\n"
        "python manage.py makemigrations <app>\n"
        "python manage.py migrate\n"
        "python manage.py showmigrations\n"
        "```\n\n"
        "После добавления поля в модель всегда запускай makemigrations + migrate.",
    ),
    (
        ["fastapi", "фастапи", "pydantic"],
        "FastAPI — современный веб-фреймворк Python с типами и автодокументацией.\n\n"
        "```python\n"
        "from fastapi import FastAPI\n"
        "from pydantic import BaseModel\n\n"
        "app = FastAPI()\n\n"
        "class Item(BaseModel):\n"
        "    name: str\n"
        "    price: float\n\n"
        "@app.post('/items/')\n"
        "def create_item(item: Item) -> Item:\n"
        "    return item\n"
        "```\n\n"
        "Валидация через Pydantic, интерактивная документация на /docs "
        "(Swagger) и /redoc. Асинхронные обработчики — через `async def`.",
    ),
    (
        ["django", "drf", "api", "serializer", "сериализатор"],
        "Django REST Framework — создание REST API на Django.\n\n"
        "```python\n"
        "from rest_framework import serializers\n\n"
        "class ItemSerializer(serializers.ModelSerializer):\n"
        "    class Meta:\n"
        "        model = Item\n"
        "        fields = ['id', 'name', 'price']\n"
        "```\n\n"
        "ViewSet + Router дают CRUD из коробки, а Parser/Throttle/Pagination "
        "настраиваются декларативно.",
    ),
    (
        ["flask", "фласк"],
        "Flask — лёгкий веб-фреймворк Python.\n\n"
        "```python\n"
        "from flask import Flask, jsonify\n\n"
        "app = Flask(__name__)\n\n"
        "@app.route('/ping')\n"
        "def ping():\n"
        "    return jsonify({'ok': True})\n"
        "```\n\n"
        "Подходит для небольших сервисов и API. Для масштабных проектов "
        "учитывай Blueprints и инъекцию зависимостей.",
    ),
    # --- JavaScript / TypeScript / React ---
    (
        ["замыкан", "closure", "замыкание", "javascript"],
        "Замыкание в JS — функция, которая запоминает переменные из области видимости, "
        "где была создана.\n\n"
        "```js\n"
        "function counter() {\n"
        "  let n = 0;\n"
        "  return () => ++n;\n"
        "}\n"
        "const c = counter();\n"
        "c(); // 1\n"
        "c(); // 2\n"
        "```\n\n"
        "Используется для приватных переменных, мемоизации, event handlers.",
    ),
    (
        ["promise", "промис", "асинхрон", "async", "await", "javascript"],
        "Promise и async/await в JS — асинхронное программирование.\n\n"
        "```js\n"
        "async function load() {\n"
        "  try {\n"
        "    const res = await fetch('/api/users');\n"
        "    const data = await res.json();\n"
        "    console.log(data);\n"
        "  } catch (e) {\n"
        "    console.error(e);\n"
        "  }\n"
        "}\n"
        "```\n\n"
        "`Promise.all` — параллельное выполнение, `Promise.race` — первое завершённое.",
    ),
    (
        ["typescript", "тип"],
        "TypeScript — типизированный надмножество JavaScript.\n\n"
        "```ts\n"
        "interface User { id: number; name: string }\n"
        "function greet(u: User): string {\n"
        "  return `Hi ${u.name}`;\n"
        "}\n"
        "```\n\n"
        "`any` — избегай, используй `unknown`, union (`'a' | 'b'`), generics `<T>`.",
    ),
    (
        ["react", "хук", "useeffect", "usestate", "компонент"],
        "React — библиотека для UI. Основные хуки:\n\n"
        "```jsx\n"
        "import { useState, useEffect } from 'react'\n\n"
        "function App() {\n"
        "  const [count, setCount] = useState(0)\n"
        "  useEffect(() => { document.title = `Count ${count}` }, [count])\n"
        "  return <button onClick={() => setCount(c => c+1)}>{count}</button>\n"
        "}\n"
        "```\n\n"
        "`useEffect(callback, deps)` — deps — зависимости, при изменении которых эффект "
        "перезапускается.",
    ),
    (
        ["next.js", "nextjs", "ssr", "ssg"],
        "Next.js — React-фреймворк с SSR/SSG.\n\n"
        "- `app/` — парадигма App Router (Next 13+)\n"
        "- Серверные компоненты (`'use server'`) и клиентские (`'use client'`)\n"
        "- `next dev` — разработка, `next build` — прод-сборка\n"
        "- Файловый роутинг: `app/page.tsx`, `app/blog/[id]/page.tsx`",
    ),
    (["javascript", "event", "событие", "делегирован"],
        "Делегирование событий в JS — вешаем один обработчик на родителя.\n\n"
        "```js\n"
        "list.addEventListener('click', (e) => {\n"
        "  const btn = e.target.closest('button');\n"
        "  if (btn) handle(btn.dataset.id);\n"
        "});\n"
        "```\n\n"
        "Эффективнее, чем обработчик на каждый элемент.",
    ),
    # --- SQL ---
    (
        ["sql", "join", "объедин"],
        "JOIN — объединение таблиц по ключу.\n\n"
        "```sql\n"
        "SELECT u.name, r.title\n"
        "FROM users u\n"
        "LEFT JOIN rooms r ON r.owner_id = u.id;\n"
        "```\n\n"
        "- `INNER JOIN` — только совпадения\n"
        "- `LEFT JOIN` — все строки слева + совпадения справа\n"
        "- `RIGHT/FULL JOIN` — аналогично",
    ),
    (
        ["sql", "индекс", "index", "оптимизац", "медлен"],
        "Индексы ускоряют SELECT, но замедляют INSERT/UPDATE.\n\n"
        "```sql\n"
        "CREATE INDEX idx_users_email ON users(email);\n"
        "```\n\n"
        "Добавляй индекс на колонки в WHERE/JOIN/ORDER BY. Используй `EXPLAIN` "
        "для анализа плана запроса.",
    ),
    (
        ["sql", "подзапрос", "subquery"],
        "Подзапрос — SELECT внутри SELECT.\n\n"
        "```sql\n"
        "SELECT name FROM users\n"
        "WHERE id IN (SELECT user_id FROM orders WHERE total > 100);\n"
        "```\n\n"
        "Эквивалентен JOIN; на больших данных JOIN часто быстрее.",
    ),
    (["sql", "запрос", "выбрат"],
        "Базовый SQL-запрос:\n\n"
        "```sql\n"
        "SELECT col1, col2\n"
        "FROM table\n"
        "WHERE condition\n"
        "GROUP BY col1\n"
        "HAVING aggregate_condition\n"
        "ORDER BY col1 DESC\n"
        "LIMIT 10;\n"
        "```"),
    # --- Git ---
    (
        ["git", "коммит", "commit"],
        "Git — система контроля версий.\n\n"
        "```bash\n"
        "git add .\n"
        "git commit -m 'описание'\n"
        "git push\n"
        "git pull\n"
        "git status\n"
        "git log --oneline\n"
        "```",
    ),
    (
        ["git", "ветка", "branch", "merge", "rebase"],
        "Ветвление в Git.\n\n"
        "```bash\n"
        "git checkout -b feature\n"
        "git merge feature       # объединить\n"
        "git rebase main         # перенести коммиты\n"
        "```\n\n"
        "`merge` сохраняет историю, `rebase` — переписывает её, делая линейной. "
        "Для локальных — rebase, для публичных — merge.",
    ),
    (
        ["git", "отменить", "revert", "reset"],
        "Отмена изменений в Git.\n\n"
        "```bash\n"
        "git reset HEAD~1      # отменить последний коммит (локально)\n"
        "git revert <hash>     # новый коммит, отменяющий изменения (для публичных)\n"
        "git checkout -- file  # отбросить незакоммиченные правки\n"
        "```\n\n"
        "Для опубликованной истории используй `revert`, никогда `reset`.",
    ),
    # --- Docker ---
    (
        ["docker", "контейне"],
        "Docker — изоляция приложений.\n\n"
        "```dockerfile\n"
        "FROM python:3.12\n"
        "WORKDIR /app\n"
        "COPY requirements.txt .\n"
        "RUN pip install -r requirements.txt\n"
        "COPY . .\n"
        "CMD [\"python\", \"manage.py\", \"runserver\", \"0.0.0.0:8000\"]\n"
        "```\n\n"
        "`docker build -t app .` и `docker run -p 8000:8000 app`.",
    ),
    (
        ["docker", "docker-compose", "композ"],
        "docker-compose — запуск нескольких контейнеров.\n\n"
        "```yaml\n"
        "services:\n"
        "  db:\n"
        "    image: postgres:16\n"
        "    environment:\n"
        "      POSTGRES_PASSWORD: secret\n"
        "  web:\n"
        "    build: .\n"
        "    ports: [\"8000:8000\"]\n"
        "    depends_on: [db]\n"
        "```\n\n"
        "`docker-compose up -d`, `docker-compose down`.",
    ),
    # --- Алгоритмы ---
    (
        ["алгоритм", "сортировк"],
        "Основные алгоритмы сортировки:\n\n"
        "- **Quicksort** — O(n log n) среднее, рекурсия с разделением\n"
        "- **Merge Sort** — O(n log n) стабильная, использует доп. память\n"
        "- **Bubble sort** — O(n²), простой, для обучения\n\n"
        "Выбирай встроенный `sort()` — оптимизирован (Timsort).",
    ),
    (
        ["сложность", "big o", "о-больш", "complexity"],
        "Big O — оценка сложности алгоритма.\n\n"
        "- O(1) — константа: доступ по индексу\n"
        "- O(log n) — бинарный поиск, дерево\n"
        "- O(n) — линейный обход\n"
        "- O(n log n) — эффективные сортировки\n"
        "- O(n²) — вложенные циклы, слабые сортировки\n\n"
        "Стремись к O(n log n) и ниже на больших данных.",
    ),
    (
        ["структур", "данных", "массив", "список", "хэш", "hash", "очередь", "стек", "дерево"],
        "Структуры данных:\n\n"
        "- **Массив/список** — O(1) доступ по индексу, O(n) вставка\n"
        "- **Хэш-таблица / словарь** — O(1) поиск\n"
        "- **Стек** — LIFO: `push`/`pop`\n"
        "- **Очередь** — FIFO: `enqueue`/`dequeue`\n"
        "- **Дерево (BST)** — O(log n) поиск\n"
        "- **Граф** — связи между узлами",
    ),
    # --- Паттерны проектирования ---
    (
        ["паттерн", "singleton", "одиночк", "factory", "фабрик", "observer", "наблюдат"],
        "Паттерны проектирования:\n\n"
        "- **Singleton** — один экземпляр класса на всё приложение\n"
        "- **Factory** — создание объектов без указания класса\n"
        "- **Observer** — уведомление зависимых объектов об изменении\n"
        "- **Strategy** — взаимозаменяемые алгоритмы\n"
        "- **Decorator** — добавление поведения без наследования",
    ),
    (
        ["mvc", "архитектур", "микросервис", "rest"],
        "Архитектура:\n\n"
        "- **MVC** — Model (данные), View (UI), Controller (логика)\n"
        "- **REST** — API по ресурсам (GET/POST/PUT/DELETE)\n"
        "- **Микросервисы** — приложение из независимых сервисов\n"
        "- **WebSocket** — двусторонний реалтайм-канал (чат, уведомления)",
    ),
    (
        ["websocket", "вебсокет"],
        "WebSocket — постоянное двустороннее соединение.\n\n"
        "```js\n"
        "const ws = new WebSocket('ws://host/ws/chat/');\n"
        "ws.onmessage = (e) => console.log(JSON.parse(e.data));\n"
        "ws.send(JSON.stringify({ action: 'message', message: 'hi' }));\n"
        "```\n\n"
        "В Django Channels — AsyncWebsocketConsumer. iPhone для чатов, "
        "уведомлений, реалтайм-обновлений.",
    ),
]

_HINTS = [
    "Я — твой ментор по языку Python. Твоя главная задача — помочь с кодом на "
    "Python: объяснить идиомы, показать примеры, подсказать лучший способ. "
    "Также разбираюсь в Django, SQL, Git, Docker, алгоритмах и паттернах.",
]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _match_query(q: str) -> str | None:
    """Возвращает ответ из базы знаний.

    Ранжирование по специфичности совпавших ключевых слов: чем длиннее ключевое
    слово и больше их совпало, тем выше приоритет записи. Это исправляет
    «первое совпадение по списку»: запрос «как сделать сортировку в python?»
    теперь попадает в раздел алгоритмов, а не в первую запись с общим словом.
    """
    best: tuple[int, str] | None = None
    for keywords, answer in _KNOWLEDGE:
        score = 0
        matched = 0
        for kw in keywords:
            if kw in q:
                score += len(kw)
                matched += 1
        if matched:
            score += matched * 2
        if score and (best is None or score > best[0]):
            best = (score, answer)
    return best[1] if best else None


def local_ai_answer(prompt: str, history: list[dict[str, Any]] | None = None) -> str | None:
    """Возвращает ответ из локальной базы, либо None, если вопрос не распознан.

    Если вопрос не распознан (уточнение, переформулировка), пересматриваются
    предыдущие сообщения пользователя из контекста: берётся первый совпавший
    вопрос пользователя и для него ищется ответ.
    """
    q = _normalize(prompt)
    ans = _match_query(q)
    if ans:
        return ans

    if history:
        for m in reversed(history):
            if m.get("is_ai"):
                continue
            prev = _normalize(m.get("text", "") or "")
            if not prev or prev == q:
                continue
            ans = _match_query(prev)
            if ans:
                return ans
    return None


def ai_help_text() -> str:
    lines = [
        "Доступные команды:",
        "",
        "`/ai <вопрос>` — спросить меня как ментора по Python",
        "`/help` — этот список",
        "",
        "Моя специализация — Python (синтаксис, идиомы, асинхронность, ООП, "
        "тесты, оптимизация). Также разбираюсь в веб-фреймворках Django, DRF, "
        "FastAPI, Flask и в SQL, Git, Docker, алгоритмах и паттернах.",
    ]
    return "\n".join(lines)
