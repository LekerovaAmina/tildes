#!/usr/bin/env sh
# Установка бэкенда на macOS / Linux (без интернета — пакеты лежат в папке wheels)
set -e
python3 -m venv .venv
. .venv/bin/activate
pip install --no-index --find-links wheels -r requirements.txt
python manage.py migrate
python manage.py load_content
echo "Готово! Запуск: ./run.sh   Администратор: .venv/bin/python manage.py createsuperuser"
