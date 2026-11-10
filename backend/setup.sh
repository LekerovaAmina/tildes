#!/usr/bin/env sh
# Установка бэкенда на macOS / Linux (без интернета — пакеты лежат в папке wheels)
set -e
python3 -m venv .venv
. .venv/bin/activate
pip install --no-index --find-links wheels -r requirements.txt
python manage.py migrate
python manage.py load_content
python manage.py ensure_admin  # admin@admin.com / admin123 — только для разработки
echo "Готово! Запуск: ./run.sh   Админка: admin@admin.com / admin123"
