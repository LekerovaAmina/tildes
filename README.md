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

Сайт берёт весь контент и прогресс с Django: фронтенд в режиме разработки проксирует `/api/*` на порт 8000. Если бэкенд не запущен, сайт покажет экран «Нет связи с сервером».

Подробности — в `backend/README.md` и `frontend/README.md`.
