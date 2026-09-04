# 🚀 JOIN WORK! — Modern Real-Time Chat

Современный real-time мессенджер уровня Telegram/Slack для команды **JOIN WORK!**.
WebSocket-общение, медиа, голосовые с транскрипцией, AI-ассистент — всё в одном.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.1-092E20?style=flat&logo=django&logoColor=white)
![Channels](https://img.shields.io/badge/Django%20Channels-4.1-094b70?style=flat&logo=django&logoColor=white)
![Daphne](https://img.shields.io/badge/Daphne-ASGI-6fbbd3?style=flat)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat&logo=next.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?style=flat&logo=typescript&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind-3-06B6D4?style=flat&logo=tailwindcss&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-FF4438?style=flat&logo=redis&logoColor=white)
![Zustand](https://img.shields.io/badge/Zustand-store-78350f?style=flat)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

## ✨ Возможности

**Общение**
- Real-time сообщения через WebSocket (Django Channels + Redis)
- Комнаты (публичные и приватные), создание/вступление/выход
- Ответы на сообщения (цитаты) и редактирование с флагом «изменено»
- Индикатор «печатает...» и онлайн-статус участников
- Счётчик непрочитанных сообщений в сайдбаре

**Медиа**
- Вложения: изображения, видео, файлы
- Запись голосовых сообщений прямо в чате (MediaRecorder)
- **Автотранскрипция голосовых в текст** (Google Web Speech API)

**Умные функции**
- **AI-ассистент** для разработки — `/ai ваш вопрос` (локальный бот или облачный Qwen)
- Поиск по сообщениям в комнате
- Закрепление важных сообщений
- Реакции-эмодзи на сообщениях (👍 ❤️ 😂 🔥)

**Интерфейс**
- Тёмная и светлая темы (авто + ручное переключение)
- Glassmorphism, плавные анимации (Framer Motion)
- Мобильная адаптивность (Mobile First)

## 🏗 Архитектура

```
├── config/                 # Django 5.1 + Channels + Daphne
│   ├── asgi.py             # ASGI с WebSocket роутингом
│   ├── settings.py         # PostgreSQL, Redis, CORS, AI
│   └── urls.py             # REST API маршруты
├── users/                  # Кастомная модель User + Auth API
├── chat/                   # Core-приложение чата
│   ├── models.py           # ChatRoom, Message, Reaction, ReadStatus
│   ├── consumers.py        # WebSocket consumer (Redis channel layer)
│   ├── serializers.py      # DRF сериализаторы
│   ├── api_views.py        # REST эндпоинты (upload, search, transcribe)
│   ├── ai_service.py       # AI-ассистент (OpenRouter + fallback)
│   ├── ai_local.py         # Локальный AI-бот (без ключа)
│   └── speech_service.py   # Транскрипция голосовых
│
└── frontend/               # Next.js 14 + TypeScript + Tailwind
    └── src/
        ├── app/            # App Router страницы
        ├── components/     # MessageBubble, ChatInput, Sidebar, ChatWindow...
        └── lib/            # Zustand store, WebSocket hook, API
```

## ⚙️ Технологии

**Backend**
- Python 3.11+, Django 5.1, Django Channels 4.1, Daphne
- PostgreSQL 15, Redis 7 (Channel Layer)
- DRF, django-cors-headers, Poetry, Ruff, Pytest
- SpeechRecognition + pydub + imageio-ffmpeg (транскрипция)
- httpx + OpenRouter (AI)

**Frontend**
- Next.js 14 (App Router), TypeScript (strict)
- Tailwind CSS, Framer Motion, Zustand, Lucide Icons

## 🚀 Быстрый старт

### 1. Инфраструктура (PostgreSQL + Redis)

```bash
docker compose up -d
```

### 2. Backend

```bash
poetry install
poetry shell

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Запуск ASGI-сервера с поддержкой WebSocket
daphne -b 0.0.0.0 -p 8000 config.asgi:application
# или
python manage.py runserver 8000
```

### 3. Frontend

```bash
cd frontend
npm install

# Windows: добавляем node в PATH
$env:Path = "C:\Users\<имя>\Documents\DEVTOOLS\nodejs-v20;" + $env:Path
npm run dev
```

Откройте **http://localhost:3000** в двух браузерах/вкладках и общайтесь!

### 4. AI-ассистент

Без ключа работает локальный бот. Для облачного Qwen задайте в `.env`:
```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

## 🤖 Как использовать AI

В поле ввода чата напишите:
```
/ai как создать модель в Django?
```
AI ответит прямо в чате зелёным пузырём.

## 🧭 API

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/auth/register/` | Регистрация |
| POST | `/api/auth/login/` | Вход |
| POST | `/api/auth/logout/` | Выход |
| GET | `/api/auth/me/` | Текущий пользователь |
| GET | `/api/chat/rooms/` | Список комнат (с непрочитанными) |
| POST | `/api/chat/rooms/create/` | Создать комнату |
| GET | `/api/chat/rooms/{id}/messages/` | История сообщений |
| GET | `/api/chat/rooms/{id}/search/?q=` | Поиск по сообщениям |
| POST | `/api/chat/rooms/{id}/upload/` | Загрузка вложения |
| POST | `/api/chat/rooms/{id}/transcribe/` | Транскрипция голосового |

**WebSocket:** `ws://localhost:8000/ws/chat/{room_name}/`

## 🚢 Деплой

Проект готов к деплою: `vercel.json` (фронтенд), `render.yaml` (бэкенд-блупринт),
поддержка `DATABASE_URL`/`REDIS_URL`. Пошаговая инструкция — в **`DEPLOY.md`**.

---

© 2026 JOIN WORK! Team. Сделано с ❤️ для победы в конкурсе.
