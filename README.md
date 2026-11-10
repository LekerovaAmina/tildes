# Tildes — тренажёр казахского языка

```
tildes/
├── backend/    Python + Django (API, админка, база). Пакеты уже скачаны в backend/wheels
└── frontend/   React + Vite (сайт)
```

## Быстрый старт

Нужны Python 3.10+ и Node.js 18+.

**1. Бэкенд** (терминал 1):

```bash
cd backend
setup.bat        # macOS/Linux: sh setup.sh   (один раз)
run.bat          # macOS/Linux: sh run.sh     → http://127.0.0.1:8000/api/
```

**2. Фронтенд** (терминал 2):

```bash
cd frontend
npm install      # один раз
npm run dev      # → http://localhost:5173
```

Сайт начинается со страницы входа: ученик регистрируется по email и паролю, и прогресс хранится в его аккаунте. Весь контент и прогресс сайт берёт с Django: в режиме разработки фронтенд проксирует `/api/*` на порт 8000. Если бэкенд не запущен, сайт покажет экран «Нет связи с сервером».

**База данных:** по умолчанию SQLite. Как подключить PostgreSQL, описано в `backend/README.md`, раздел «База данных».

**Админ-панель:** войдите на сайте как **admin@admin.com / admin123**, и откроется http://localhost:5173/panel. Это учётка только для разработки: на сервере с `DJANGO_DEBUG=0` пароль `admin123` не сработает.

Подробности — в `backend/README.md` и `frontend/README.md`.
