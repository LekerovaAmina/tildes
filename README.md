# Tildes — тренажёр казахского языка

```
tildes/
├── backend/        Python + Django (API, админка, база)
├── frontend/       React + Vite (сайт)
├── infra/          docker-compose.yml — запуск всего проекта в Docker
└── .env.example    настройки для Docker (пароль БД и т.п.)
```

## Быстрый старт (Docker) — рекомендуется

Нужен только [Docker Desktop](https://www.docker.com/products/docker-desktop/). Python, Node.js и PostgreSQL ставить не нужно.

```bash
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env  (необязательно)
docker compose --env-file .env -f infra/docker-compose.yml up --build
```

Поднимаются 4 сервиса:

| Сервис | Что это | Адрес |
|---|---|---|
| `db` | PostgreSQL 16, данные в volume `pgdata` | `localhost:5433` |
| `redis` | Redis 7 (зарезервирован, Django пока не использует) | `localhost:6379` |
| `core` | Django. При старте сам выполняет `migrate`, `load_content` и `ensure_admin` | http://localhost:8000/api/ |
| `frontend` | Vite dev-сервер, проксирует `/api` на `core` | http://localhost:5173 |

Код `backend/` и `frontend/` примонтирован в контейнеры: правки применяются сразу, без пересборки. Пересобирать (`up --build`) нужно только после изменения `requirements.txt`, `package.json` или Dockerfile.

Частые команды:

```bash
docker compose -f infra/docker-compose.yml up -d                          # в фоне
docker compose -f infra/docker-compose.yml logs -f core                   # логи Django
docker compose -f infra/docker-compose.yml exec core python manage.py test learning
docker compose -f infra/docker-compose.yml down                           # остановить (база сохранится)
docker compose -f infra/docker-compose.yml down -v                        # остановить и удалить базу
```

Подробный разбор каждого файла — в `DOCKER_GUIDE.md`.

## Запуск без Docker (запасной вариант)

Нужны Python 3.10+, Node.js 18+ и запущенный PostgreSQL 16 (как создать базу — `backend/README.md`, раздел «База данных»).

**1. Бэкенд** (терминал 1):

```bash
cd backend
cp .env.example .env              # впишите POSTGRES_PASSWORD; PowerShell: Copy-Item .env.example .env
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py load_content
python manage.py ensure_admin     # admin@admin.com / admin123
python manage.py runserver 8000   # → http://127.0.0.1:8000/api/
```

На macOS/Linux то же самое делают `sh setup.sh` (один раз) и `sh run.sh`.

**2. Фронтенд** (терминал 2):

```bash
cd frontend
npm install      # один раз
npm run dev      # → http://localhost:5173
```

## Как всё устроено

Сайт начинается со страницы входа: ученик регистрируется по email и паролю, и прогресс хранится в его аккаунте. Весь контент и прогресс сайт берёт с Django: в режиме разработки Vite проксирует `/api/*` на бэкенд (`127.0.0.1:8000`, а в Docker — `core:8000`). Если бэкенд не запущен, сайт покажет экран «Нет связи с сервером».

- **База данных:** только PostgreSQL. Подробности — в `backend/README.md`.
- **Документация API:** http://localhost:8000/api/docs/ (Swagger).
- **Админ-панель:** войдите на сайте как **admin@admin.com / admin123**, откроется http://localhost:5173/admin. Это учётка только для разработки: на сервере с `DJANGO_DEBUG=0` пароль `admin123` не сработает.

Подробности — в `backend/README.md` и `frontend/README.md`.
