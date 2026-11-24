#!/usr/bin/env sh
# Установка бэкенда без Docker (macOS / Linux / Git Bash). Пакеты скачиваются из PyPI
set -e
# База — PostgreSQL: сначала заполните .env (см. .env.example и README.md)
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан файл .env — впишите в него пароль PostgreSQL (POSTGRES_PASSWORD) и запустите setup.sh снова."
  exit 1
fi
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py load_content
python manage.py ensure_admin  # admin@admin.com / admin123 — только для разработки
echo "Готово! Запуск: ./run.sh   Админка: admin@admin.com / admin123"
