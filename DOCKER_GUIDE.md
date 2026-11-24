# Tildes в Docker: пошаговый гайд (делаем сами)

## Что мы делаем и зачем

Сейчас, чтобы запустить проект, нужно вручную:
1. поставить PostgreSQL, создать базу и пользователя;
2. поставить Python, создать `.venv` и установить зависимости;
3. поставить Node.js и сделать `npm install`;
4. запустить `migrate`, `load_content`, `runserver` и `npm run dev` в разных окнах.

Мы опишем всё это в файлах.
- **Docker** упаковывает каждую часть приложения в **контейнер**: изолированный мини-Linux,
  в котором уже стоит нужная версия Python, Node или PostgreSQL.
- **Образ** — шаблон контейнера. Его рецепт пишется в `Dockerfile`.
- **Docker Compose** поднимает несколько контейнеров одной командой, соединяет их
  в общую сеть и запускает в правильном порядке.

Должно получиться 4 сервиса:

| Сервис | Что внутри | Порт на вашем ПК |
|---|---|---|
| `db` | PostgreSQL 16, данные в volume | 5433 |
| `redis` | Redis (пока Django его не использует) | 6379 |
| `core` | Django; при старте выполняет migrate + load_content | 8000 |
| `frontend` | React + Vite | 5173 |

```
                 браузер
       localhost:5173 │          localhost:8000 (API, Swagger)
                      ▼                 ▼
┌──────────────── сеть docker compose ──────────────────┐
│ frontend (Vite) ──/api, /django-admin──▶ core (Django) │
│                                           │       │    │
│                                           ▼       ▼    │
│                                    db (Postgres) redis │
└────────────────────────────────────────┼───────────────┘
                                         ▼
                              volume pgdata (данные БД)
```

Итоговая структура новых файлов:
```
tildes/
├── .gitattributes                  ← шаг 1
├── backend/
│   ├── .dockerignore               ← шаг 2
│   ├── docker-entrypoint.sh        ← шаг 3
│   └── Dockerfile                  ← шаг 4
├── frontend/
│   ├── .dockerignore               ← шаг 5
│   ├── Dockerfile                  ← шаг 6
│   └── vite.config.js              ← шаг 7 (правка)
├── infra/
│   └── docker-compose.yml          ← шаг 9
├── .env.example                    ← шаг 8 (корневой)
└── README.md                       ← шаг 12 (обновлён)

Удалено (шаг 11): backend/wheels/, backend/setup.bat, backend/run.bat
```

---

## Шаг 0. Docker Desktop

Установите Docker Desktop, запустите его и дождитесь статуса «Engine running». Проверка:
```powershell
docker info
```
Если команда выводит информацию о сервере без ошибки `failed to connect`, Docker готов.

---

## Шаг 1. `.gitattributes` (в корне репозитория)

```
*.sh text eol=lf
```

**Зачем.** На Windows git часто сохраняет файлы с переводами строк CRLF (`\r\n`). Shell-скрипт
с `\r` в Linux-контейнере падает с ошибкой `/bin/sh^M: not found`. Эта строка говорит git
всегда хранить `.sh` с LF.

---

## Шаг 2. `backend/.dockerignore`

```
.venv/
__pycache__/
*.pyc
.env
.env.*
!.env.example
db.sqlite3*
media/
wheels/
```

**Зачем.** Это как `.gitignore`, только для команды `COPY . .` в Dockerfile. Без него в образ
попадут:
- `.venv` — сотни мегабайт, к тому же собранные под Windows;
- `.env` — ваш пароль от базы;
- `wheels/` — пакеты под Windows. Контейнер работает на Linux, pip скачает нужные версии сам.

---

## Шаг 3. `backend/docker-entrypoint.sh`

```sh
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
```

**Построчно:**
- `#!/bin/sh` — какой интерпретатор запускает скрипт.
- `set -e` — если любая команда упала, скрипт сразу останавливается. Вы увидите ошибку,
  а не наполовину рабочий сервер.
- `migrate --noinput` — создаёт или обновляет таблицы в PostgreSQL. Запускать при каждом
  старте безопасно: уже применённые миграции пропускаются. `--noinput` — не задавать вопросов.
- `load_content` — загружает уроки из `learning/data/content.json`. Команда обновляет данные,
  а не дублирует их, и прогресс учеников не трогает. Поэтому её тоже можно запускать каждый раз.
- `ensure_admin` — создаёт `admin@admin.com / admin123`, если такого пользователя ещё нет
  (то же самое делает `setup.sh`). Этот шаг необязательный, можно удалить.
  `|| echo ...` нужен, чтобы при `DJANGO_DEBUG=0` ошибка этой команды не роняла весь старт.
- `exec "$@"` — запускает команду из `CMD` Dockerfile (runserver) **вместо** скрипта.
  Благодаря `exec` Django получает сигнал остановки напрямую, и `docker compose stop`
  срабатывает мгновенно.

> Сохраните файл с переводами строк **LF**: в VS Code внизу справа нажмите `CRLF` и
> выберите `LF`. На всякий случай Dockerfile из шага 4 тоже чистит `\r`.

---

## Шаг 4. `backend/Dockerfile`

```dockerfile
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

**Построчно:**
- `FROM python:3.13-slim` — **базовый образ**: готовый Linux с Python 3.13. `slim` —
  урезанная версия, весит меньше. Каждая следующая инструкция добавляет «слой» поверх.
- `ENV ...` — переменные окружения внутри контейнера:
  - `PYTHONDONTWRITEBYTECODE=1` — не создавать `.pyc`. Код будет примонтирован с вашего
    диска, иначе в папке `backend` появится мусор от контейнера;
  - `PYTHONUNBUFFERED=1` — логи Django сразу видны в `docker compose logs`, без задержки;
  - `PIP_NO_CACHE_DIR=1` — pip не хранит кеш, образ получается меньше;
  - `PIP_DISABLE_PIP_VERSION_CHECK=1` — без предупреждений «доступна новая версия pip».
- `WORKDIR /app` — рабочая папка внутри контейнера. Дальнейшие команды выполняются в ней.
- `COPY requirements.txt .` + `RUN pip install ...` — **сначала только зависимости.**
  Docker кеширует каждый слой. Пока `requirements.txt` не меняется, этот шаг при
  пересборке берётся из кеша и занимает секунды. Если сначала скопировать весь код, любая
  правка в `views.py` заново запускала бы установку всех пакетов.
- `COPY . .` — копируем код в образ. В compose папка всё равно будет примонтирована поверх,
  но с этой строкой образ работает и сам по себе.
- `COPY docker-entrypoint.sh /usr/local/bin/...` — кладём скрипт **вне** `/app`, потому что
  монтирование перекрывает `/app` целиком.
- `sed -i 's/\r$//'` удаляет Windows-символы `\r`, `chmod +x` делает файл исполняемым.
- `EXPOSE 8000` — документация: контейнер слушает порт 8000.
- `ENTRYPOINT` — выполняется при **каждом** старте контейнера, это наш скрипт из шага 3.
- `CMD` — команда по умолчанию, её запускает `exec "$@"` в конце скрипта.
  Адрес `0.0.0.0` обязателен: с `127.0.0.1` Django был бы доступен только изнутри
  самого контейнера.

---

## Шаг 5. `frontend/.dockerignore`

```
node_modules/
dist/
.env
.env.*
!.env.example
```

**Зачем.** Ваш `node_modules` собран под Windows (например, бинарник `esbuild.exe`), в Linux
он не заработает. Контейнер поставит свои пакеты сам.

---

## Шаг 6. `frontend/Dockerfile`

```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

**Построчно:**
- `node:22-alpine` — Node.js 22 на маленьком Alpine Linux.
- Сначала `package*.json`, потом `npm ci` — тот же приём с кешем, что и для pip.
  `npm ci` ставит **точно** те версии, что записаны в `package-lock.json`. `npm install`
  мог бы их обновить.
- `COPY . .` — код.
- `CMD ... --host 0.0.0.0` — Vite слушает все интерфейсы, иначе браузер на вашем ПК
  до него не достучится. `--` передаёт аргументы дальше, в команду `vite`.

---

## Шаг 7. Правка `frontend/vite.config.js`

**Проблема.** Сейчас прокси жёстко направлен на `http://127.0.0.1:8000`. Внутри контейнера
`frontend` адрес `127.0.0.1` указывает на сам контейнер `frontend`, а Django живёт в другом
контейнере, по адресу `http://core:8000`.

**Решение:** брать адрес из переменной окружения, а без неё оставлять старое значение.
Заодно включаем опрос файлов: на Windows и macOS Docker не передаёт в контейнер события
«файл изменился», и без опроса горячая перезагрузка не работает.

Файл целиком после правки:
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Куда проксировать запросы к Django. Локально — 127.0.0.1:8000,
// в Docker — http://core:8000 (имя сервиса из infra/docker-compose.yml)
const API_TARGET = process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // В Docker на Windows/macOS включаем опрос файлов, чтобы работала горячая перезагрузка
    watch: process.env.CHOKIDAR_USEPOLLING === 'true' ? { usePolling: true, interval: 300 } : undefined,
    // Запросы /api/* уходят на Django (backend, порт 8000)
    // /django-admin и /static — Django-админка на том же адресе, чтобы после входа сессия сразу работала.
    // /admin — это админ-панель самого сайта (React), её Vite отдаёт сам
    proxy: {
      '/api': API_TARGET,
      '/django-admin': API_TARGET,
      '/static': API_TARGET,
      // Загруженные картинки карточек (MEDIA_URL Django)
      '/media': API_TARGET,
    },
  },
})
```
Без Docker обе переменные не заданы, и `npm run dev` работает как раньше.

---

## Шаг 8. Корневой `.env.example` (уже создан)

Файл лежит в **корне** репозитория, а не в `infra/`: так все настройки проекта находятся в одном
месте, на виду.

```
POSTGRES_DB=tildes
POSTGRES_USER=tildes
POSTGRES_PASSWORD=tildes
```

**Как это работает.**
- `.env.example` — шаблон, он хранится в git. Настоящий `.env` вы создаёте сами
  (`Copy-Item .env.example .env`) и пишете в него свои пароли. В git `.env` не попадёт:
  в корневой `.gitignore` добавлены строки `.env`, `.env.*` и `!.env.example`
  (последняя значит «а шаблон всё-таки хранить»).
- Сам compose автоматически читает `.env` только из **папки compose-файла** (`infra/`).
  Корневой файл нужно указать явно флагом `--env-file .env` (см. шаг 10).
- Значения подставляются в записи вида `${POSTGRES_DB:-tildes}` в compose-файле.
  Если `.env` нет, берётся то, что после `:-`, то есть `tildes`. Поэтому проект запускается
  и без `.env`.
- `backend/.env` по-прежнему нужен только для запуска **без** Docker.

---

## Шаг 9. `infra/docker-compose.yml`

```yaml
name: tildes

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-tildes}
      POSTGRES_USER: ${POSTGRES_USER:-tildes}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-tildes}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5433:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-tildes} -d ${POSTGRES_DB:-tildes}"]
      interval: 5s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  core:
    build:
      context: ../backend
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-tildes}
      POSTGRES_USER: ${POSTGRES_USER:-tildes}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-tildes}
      POSTGRES_HOST: db
      POSTGRES_PORT: "5432"
      REDIS_URL: redis://redis:6379/0
      DJANGO_DEBUG: "1"
      DJANGO_ALLOWED_HOSTS: localhost,127.0.0.1,core
    volumes:
      - ../backend:/app
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  frontend:
    build:
      context: ../frontend
    restart: unless-stopped
    environment:
      VITE_PROXY_TARGET: http://core:8000
      CHOKIDAR_USEPOLLING: "true"
    volumes:
      - ../frontend:/app
      - frontend_node_modules:/app/node_modules
    ports:
      - "5173:5173"
    depends_on:
      - core

volumes:
  pgdata:
  frontend_node_modules:
```

### Разбор по блокам

**`name: tildes`** — имя проекта. Контейнеры будут называться `tildes-core-1`, `tildes-db-1`
и так далее, volume — `tildes_pgdata`.

**`restart: unless-stopped`** — если контейнер упал, Docker перезапустит его сам. Не
перезапускает, только если вы остановили его вручную.

#### `db`
- `image: postgres:16-alpine` — готовый официальный образ, свой Dockerfile не нужен.
- `environment` — при **первом** запуске образ сам создаёт базу и пользователя с этими данными.
  Запись `${POSTGRES_DB:-tildes}` значит «взять из корневого `.env` (флаг `--env-file .env`), а если там пусто —
  `tildes`».
- `volumes: pgdata:/var/lib/postgresql/data` — **volume для базы.** Контейнер одноразовый:
  при `docker compose down` он удаляется вместе со всем содержимым. Volume — отдельное
  хранилище, которым управляет Docker. PostgreSQL хранит данные в `/var/lib/postgresql/data`,
  а мы подключаем туда volume, поэтому пользователи и прогресс переживают перезапуски.
- `ports: "5433:5432"` — запись в формате `порт_на_ПК:порт_в_контейнере`. База доступна
  снаружи на `localhost:5433` (для DBeaver или pgAdmin). Выбран 5433, чтобы не конфликтовать
  с локальным PostgreSQL на 5432.
- `healthcheck` — **проверка готовности.** Запущенный контейнер ещё не значит, что база
  принимает подключения: инициализация занимает несколько секунд. `pg_isready` выполняется
  каждые 5 секунд, до 10 попыток. Пока проверка не пройдёт, сервис в статусе `starting`.

#### `redis`
Хранилище «ключ–значение» в памяти. **Сейчас Django его не использует.** Мы поднимаем его
заранее и передаём адрес в `core` через `REDIS_URL`. Пригодится для кеша, очередей (Celery)
и rate limit. Чтобы подключить: добавить пакет `redis` в `requirements.txt` и настройку
`CACHES` в `settings.py`. Healthcheck `redis-cli ping` ждёт ответа `PONG`.

#### `core` (Django)
- `build.context: ../backend` — собрать образ из `backend/Dockerfile`. Путь считается от папки
  с compose-файлом (`infra/`), поэтому `../`.
- `POSTGRES_HOST: db` — **главное про сеть compose:** все сервисы находятся в одной внутренней
  сети, а **имя сервиса служит адресом хоста**. Внутри контейнера `127.0.0.1` — это сам `core`,
  базы там нет, поэтому подключаемся к `db`.
- Ваш `backend/.env` с `POSTGRES_HOST=127.0.0.1` мешать не будет: `settings.py` читает его через
  `load_dotenv`, но `load_dotenv` **не перезаписывает** переменные, которые уже задал compose.
- `DJANGO_ALLOWED_HOSTS` — добавили `core`, чтобы Django принимал запросы по внутреннему
  имени сервиса.
- `volumes: ../backend:/app` — **код монтируется** (bind mount): ваша папка `backend` видна
  в контейнере как `/app`. Правите файл в редакторе, `runserver` замечает изменение и
  перезапускается. Пересобирать образ нужно только после изменения `requirements.txt`
  или `Dockerfile`.
- `depends_on ... condition: service_healthy` — запускать `core` только после того, как
  healthcheck базы **прошёл**. Иначе `migrate` упадёт с «connection refused». Обычный
  `depends_on: [db]` ждёт только старта контейнера, а не готовности базы.

#### `frontend` (Vite)
- `VITE_PROXY_TARGET: http://core:8000` — сюда Vite проксирует `/api`, `/django-admin`,
  `/static` и `/media` (переменная из шага 7).
- `CHOKIDAR_USEPOLLING: "true"` — включает опрос файлов из шага 7.
- `../frontend:/app` — монтирование кода.
- `frontend_node_modules:/app/node_modules` — отдельный volume **поверх** `node_modules`.
  Он закрывает Windows-версию `node_modules` с вашего диска, и контейнер использует
  Linux-пакеты, которые поставил `npm ci` при сборке.

#### `volumes:` внизу
Объявление именованных volume, которые используются выше.

---

## Шаг 10. Запуск

Из корня репозитория:
```powershell
Copy-Item .env.example .env
```
```powershell
docker compose --env-file .env -f infra/docker-compose.yml up --build
```
- `--env-file .env` — откуда брать переменные (`POSTGRES_PASSWORD` и др.), см. шаг 8;
- `-f infra/docker-compose.yml` — какой compose-файл использовать;
- `up` — создать и запустить все сервисы;
- `--build` — собрать или пересобрать образы. Первый раз уйдёт несколько минут: скачиваются
  образы, ставятся пакеты.

Что должно появиться в логах, по порядку:
1. `db` — `database system is ready to accept connections`;
2. `core` — `==> Миграции`, `==> Загрузка контента`, `Starting development server at http://0.0.0.0:8000/`;
3. `frontend` — `VITE ... ready`.

Откройте в браузере:
- сайт: http://localhost:5173
- админ-панель сайта: http://localhost:5173/admin (`admin@admin.com` / `admin123`)
- Swagger: http://localhost:8000/api/docs/
- Django-админка: http://localhost:5173/django-admin/

Остановить: `Ctrl+C` в окне с логами.

---

## Шаг 11. Уборка: удалены `backend/wheels/`, `setup.bat`, `run.bat` (сделано)

**Что было.** В `backend/wheels/` лежали заранее скачанные пакеты (`.whl`), в основном под
Windows и Python 3.10–3.13. `setup.bat` ставил их без интернета, а `run.bat` запускал
`runserver`.

**Почему удалили.**
- Docker собирает Linux-образ, и Windows-колёса ему не подходят: pip всё равно скачивает
  пакеты из PyPI. Папка только раздувала репозиторий (бинарники в git).
- `.bat`-скрипты дублировали Docker: теперь установку и запуск делает одна команда
  из шага 10.
- `setup.sh` и `run.sh` оставлены для запуска без Docker на macOS/Linux. Из `setup.sh`
  убран флаг `--find-links wheels`, пакеты теперь ставятся просто из PyPI.
- Подсказки на сайте («Запустите бэкенд: run.bat») в `ServerGate.jsx` и `api/client.js`
  заменены на команду Docker и ссылку на README.

Файлы удалены через `git rm`, поэтому их всегда можно вернуть из истории git:
```powershell
git checkout HEAD -- backend/wheels backend/setup.bat backend/run.bat
```

Строка `wheels/` в `backend/.dockerignore` теперь лишняя, но безвредная: её можно убрать.

## Шаг 12. README обновлены (сделано)

- **Корневой `README.md`**: главный способ запуска — Docker (одна команда, таблица сервисов
  и портов, частые команды). Раздел «Запуск без Docker (запасной вариант)» описывает
  ручные шаги: `venv`, `pip install`, `migrate`, `load_content`, `runserver`, `npm run dev`.
- **`backend/README.md`**: раздел «Установка» разделён на «Через Docker» и «Без Docker»,
  из структуры убраны `wheels/` и `.bat`, добавлены `Dockerfile` и `docker-entrypoint.sh`.
  Отмечено, что ручное создание базы в pgAdmin нужно только без Docker.
- **`frontend/README.md`**: добавлен запуск через Docker и объяснение `VITE_PROXY_TARGET`.

---

## Полезные команды

| Команда | Что делает |
|---|---|
| `docker compose -f infra/docker-compose.yml up -d` | Запустить в фоне (`-d` = detached) |
| `docker compose -f infra/docker-compose.yml ps` | Статус сервисов |
| `docker compose -f infra/docker-compose.yml logs -f core` | Логи Django в реальном времени |
| `docker compose -f infra/docker-compose.yml exec core python manage.py test` | Выполнить команду в работающем контейнере |
| `docker compose -f infra/docker-compose.yml exec db psql -U tildes` | Консоль PostgreSQL |
| `docker compose -f infra/docker-compose.yml down` | Остановить и удалить контейнеры (**данные БД сохраняются**) |
| `docker compose -f infra/docker-compose.yml down -v` | То же **плюс удалить volume**: база станет пустой |

Если перейти в папку `infra` (`cd infra`), флаг `-f infra/docker-compose.yml` можно не писать.

## Частые проблемы

- **`port is already allocated`** — порт уже занят, например локальным `runserver` или
  `npm run dev`. Остановите их или поменяйте левое число в `ports:`.
- **`failed to connect to the docker API`** — Docker Desktop не запущен.
- **`/bin/sh^M: not found`** — скрипт сохранён с CRLF (см. шаги 1 и 3).
- **Добавили пакет в `package.json`, а контейнер его не видит** — volume хранит старые
  `node_modules`. Выполните `down`, затем `docker volume rm tildes_frontend_node_modules`,
  затем `up --build`.
- **Поменяли `POSTGRES_PASSWORD`, и Django не подключается** — пароль применяется только при
  первой инициализации volume. Верните старый пароль или выполните `down -v` (база удалится).
