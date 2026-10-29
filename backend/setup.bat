@echo off
chcp 65001 >nul
REM Установка бэкенда на Windows (без интернета — пакеты лежат в папке wheels)
python -m venv .venv || goto :error
call .venv\Scripts\activate.bat
python -m pip install --no-index --find-links wheels -r requirements.txt || goto :error
python manage.py migrate || goto :error
python manage.py load_content || goto :error
echo.
echo Готово! Запуск сервера: run.bat
echo Создать администратора: .venv\Scripts\python manage.py createsuperuser
goto :eof
:error
echo Ошибка установки. Проверьте, что установлен Python 3.10+ (python --version).
exit /b 1
