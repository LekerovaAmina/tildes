#!/bin/sh
# Выполняется при каждом старте контейнера core, перед основной командой (runserver).
set -e

echo "==> Миграции"
python manage.py migrate --noinput

echo "==> Загрузка контента (data/content.json)"
python manage.py load_content

echo "==> Админ по умолчанию (только для разработки)"
python manage.py ensure_admin || echo "ensure_admin пропущен"

# Запускаем то, что передано в CMD (по умолчанию — runserver)
exec "$@"