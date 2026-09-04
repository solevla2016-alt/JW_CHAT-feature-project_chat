# 🚀 JOIN WORK! — Modern Real-Time Chat

Современный реально-временный мессенджер уровня Telegram/Slack для команды **JOIN WORK!**.

## ✨ Возможности

- **Real-time обмен сообщениями** через WebSocket (Django Channels + Redis)
- **Ответы на сообщения** (Replies) с отображением цитаты
- **Редактирование сообщений** с флагом "изменено"
- **Индикатор набора текста** ("печатает...") с debounce 3 сек
- **Онлайн-статус** участников
- **Оптимистичный UI** — мгновенная отправка
- **Тёмная и светлая тема** (авто + ручное переключение)
- **Glassmorphism** эффекты, плавные анимации (Framer Motion)
- **Мобильная адаптивность** (Mobile First)
- **История сообщений** (последние 50-100)

## 🏗 Архитектура

```
├── config/                 # Django 5.1 + Channels + Daphne
│   ├── asgi.py             # ASGI с WebSocket роутингом
│   ├── settings.py         # PostgreSQL, Redis, CORS
│   └── urls.py             # REST API маршруты
├── users/                  # Кастомная модель User + Auth API
├── chat/                   # Core-приложение чата
│   ├── models.py           # ChatRoom, Message (reply_to, is_edited)
│   ├── consumers.py        # WebSocket consumer (Redis channel layer)
│   ├── serializers.py      # DRF сериализаторы
│   └── api_views.py        # REST эндпоинты
│
└── frontend/               # Next.js 14 + TypeScript + Tailwind
    └── src/
        ├── app/            # App Router страницы
        ├── components/     # MessageBubble, ChatInput, Sidebar...
        └── lib/            # Zustand store, WebSocket hook, API
```

## ⚙️ Технологии

**Backend**
- Python 3.11+, Django 5.1, Django Channels 4.1, Daphne
- PostgreSQL 15, Redis 7 (Channel Layer)
- DRF, django-cors-headers, Poetry, Ruff, Pytest

**Frontend**
- Next.js 14 (App Router), TypeScript (strict)
- Tailwind CSS, Framer Motion, Zustand, Lucide Icons

## 🚀 Быстрый старт

### 1. Запуск инфраструктуры (PostgreSQL + Redis)

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
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Откройте **http://localhost:3000** в двух браузерах/вкладках и общайтесь!

## 🧭 API

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/auth/register/` | Регистрация |
| POST | `/api/auth/login/` | Вход |
| POST | `/api/auth/logout/` | Выход |
| GET | `/api/auth/me/` | Текущий пользователь |
| GET | `/api/chat/rooms/` | Список комнат |
| POST | `/api/chat/rooms/create/` | Создать комнату |
| GET | `/api/chat/rooms/{id}/messages/` | История сообщений |

**WebSocket:** `ws://localhost:8000/ws/chat/{room_name}/`

---

© 2026 JOIN WORK! Team. Сделано с ❤️ для победы в конкурсе.
