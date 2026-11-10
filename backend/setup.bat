@echo off
chcp 65001 >nul
REM Установка бэкенда на Windows (без интернета — пакеты лежат в папке wheels)
python -m venv .venv || goto :error
call .venv\Scripts\activate.bat
python -m pip install --no-index --find-links wheels -r requirements.txt || goto :error
python manage.py migrate || goto :error
python manage.py load_content || goto :error
REM Админ для разработки: admin@admin.com / admin123 (см. learning/management/commands/ensure_admin.py)
python manage.py ensure_admin || goto :error
echo.
echo Готово! Запуск сервера: run.bat
echo Админка: войдите как admin@admin.com / admin123
goto :eof
:error
echo Ошибка установки. Проверьте, что установлен Python 3.10+ (python --version).
exit /b 1
