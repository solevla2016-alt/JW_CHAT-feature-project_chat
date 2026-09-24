#!/bin/sh
set -e

echo "[entrypoint] applying migrations..."
python manage.py migrate --noinput

echo "[entrypoint] collecting static..."
python manage.py collectstatic --noinput || echo "[entrypoint] collectstatic skipped (no static)"

echo "[entrypoint] starting daphne on :8000"
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application