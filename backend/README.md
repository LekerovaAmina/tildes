# Tildes — бэкенд (Python + Django)

Django 5.1 + Django REST Framework + django-cors-headers + drf-spectacular. База — **только PostgreSQL** (16+).
Пакеты лежат в папке `wheels/`; под Windows и Python 3.13 установка работает **без интернета**, в остальных случаях недостающие пакеты скачиваются из PyPI.

## Установка

Нужен Python 3.10+ (`python --version`) и запущенный PostgreSQL. Сначала создайте базу и `.env` — см. раздел [PostgreSQL](#база-данных) ниже.

**Windows:** дважды щёлкните `setup.bat` (или запустите в терминале), затем `run.bat`.

**macOS / Linux:**

```bash
sh setup.sh
sh run.sh
```

Скрипт создаёт виртуальное окружение `.venv`, ставит пакеты из `wheels/`, создаёт базу и загружает контент B2.

Вручную то же самое:

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install --find-links wheels -r requirements.txt
python manage.py migrate
python manage.py load_content
python manage.py runserver 8000
```

- API: http://127.0.0.1:8000/api/levels/
- Документация API (Swagger UI): http://127.0.0.1:8000/api/docs/ — схема OpenAPI: http://127.0.0.1:8000/api/schema/
  (сохранить в файл: `python manage.py spectacular --file schema.yaml`)
- Админка (редактирование слов, тем, вопросов): http://127.0.0.1:8000/django-admin/ — сначала `python manage.py createsuperuser`
- Тесты: `python manage.py test learning`

## Структура

```
backend/
├── config/            настройки Django (settings.py, urls.py)
├── learning/          приложение
│   ├── models.py      схема БД: 23 таблицы (см. раздел «База данных»)
│   ├── services.py    баллы и их журнал, ранги, серия дней, взвешенная колода повторения
│   ├── views.py       API
│   ├── urls.py        маршруты /api/...
│   ├── admin.py       админка + журнал изменений (audit_log)
│   ├── data/content.json                    контент B2 (10 модулей, 225 слов, 50 вопросов)
│   └── management/commands/load_content.py  загрузка/обновление контента
├── db/schema.sql      справочный DDL для PostgreSQL 16
├── wheels/            скачанные пакеты (Django, DRF, CORS и зависимости)
├── requirements.txt
└── setup.bat / setup.sh / run.bat / run.sh
```

## База данных

23 таблицы (имена совпадают с макетом), плюс служебные таблицы Django (`django_*`, `auth_*`) и `authtoken_token` — токены входа.

| Группа | Таблицы |
|---|---|
| Пользователи | `users` (свой пользователь Django: email вместо логина, роли student / editor / admin) |
| Контент | `levels` → `modules` → `lessons` → `lesson_blocks`, `words`, `texts`, `grammar_rules` (`grammar_table_rows`, `grammar_examples`), `quizzes` (`quiz_questions` → `quiz_options`); `media_files` |
| Админка | `audit_log` — кто, что и когда изменил в админке |
| Прогресс | `point_transactions`, `user_activity_days`, `user_word_progress`, `user_lesson_progress`, `card_sessions` → `card_answers`, `quiz_attempts` → `quiz_attempt_answers` |

Зарезервированы на будущее: `listening_tasks`, `speaking_tasks`, `writing_tasks`.

- У контента есть статус `draft / review / published / archived`; API отдаёт только опубликованное.
- `users.points` — сумма записей `point_transactions` (хранится для быстрого рейтинга).
- В `content.json` у модуля 4 урока заданы только названиями, поэтому слова, грамматика, текст и тест модуля загружаются в его первый урок. Их можно разнести по урокам в админке — API соберёт тему обратно.

**PostgreSQL:**

1. В pgAdmin создайте пользователя (Login/Group Role) `tildes` с паролем и правом входа (Can login), затем базу `tildes` с владельцем `tildes`.
   Для запуска тестов (`python manage.py test`) пользователю нужно право создавать базы: `ALTER ROLE tildes CREATEDB;`
2. Скопируйте `.env.example` в `.env` (рядом с `manage.py`) и впишите пароль в `POSTGRES_PASSWORD`. Файл `.env` в git не попадает.
   Там же `DJANGO_ALLOWED_HOSTS` — домены, с которых Django принимает запросы (через запятую).
3. Драйвер `psycopg` входит в `requirements.txt` (под Windows лежит в `wheels/`).
4. Создайте таблицы и загрузите контент: `python manage.py migrate`, затем `python manage.py load_content`.
5. Создайте администратора: `python manage.py createsuperuser` (email и пароль).

SQLite больше не поддерживается: старый `db.sqlite3` можно удалить.

## Пользователь и вход

Сайт сначала просит войти или зарегистрироваться (фронтенд не пускает дальше `/auth` без входа). API при этом по-прежнему умеет анонимный режим: без токена пользователь определяется по заголовку `X-Device-Id` — по нему создаётся запись в `users` с техническим email `<id>@device.tildes.local` и без пароля.

Вход по email и паролю — `learning/auth.py`, токены хранятся в таблице `authtoken_token`. Клиент шлёт `Authorization: Token <key>`; если заголовок есть, весь API (прогресс, карточки, рейтинг) работает от вошедшего пользователя. При регистрации с `X-Device-Id` анонимный пользователь устройства становится аккаунтом — баллы и прогресс сохраняются. Страница входа на сайте: http://localhost:5173/auth.

| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/auth/register/` | `{email, password, name?}` → `{token, user}` (201) |
| POST | `/api/auth/login/` | `{email, password}` → `{token, user}`; неверный email или пароль → 401 `{detail}` |
| POST | `/api/auth/logout/` | удаляет токен (нужен `Authorization`) |
| GET | `/api/auth/me/` | `{user}` (нужен `Authorization`) |

Пароль проверяется стандартными валидаторами Django (≥ 8 символов, не только цифры, не из списка популярных). Вход и регистрация ограничены 20 запросами в минуту с IP (`AUTH_THROTTLE_RATE`).

Сотрудники входят в админку по email и паролю (`python manage.py createsuperuser`). Роль `editor` может менять только контент.

## API админ-панели

Для экрана `/admin` на фронтенде (макет Figma «Tildes — админ-панель»), код в `learning/panel_api.py`. Доступ только у admin и editor, с заголовком `Authorization: Token …`. Все изменения пишутся в `audit_log`.

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/api/panel/dashboard/` | счётчики, покрытие уровней, черновики, активность учеников, последние изменения |
| GET | `/api/panel/search/?q=` | поиск по урокам и словам |
| GET / POST | `/api/panel/levels/` | уровни; создать уровень |
| PATCH | `/api/panel/levels/<code>/` | названия, описание, «виден ученикам» |
| GET / POST | `/api/panel/levels/<code>/modules/` | модули с уроками; создать модуль |
| POST | `/api/panel/levels/<code>/modules/reorder/` | `{ids}` — порядок модулей |
| PATCH | `/api/panel/modules/<id>/` | названия, эмодзи, цвет, статус |
| POST | `/api/panel/modules/<id>/lessons/` | новый урок (черновик) |
| GET / PATCH / DELETE | `/api/panel/lessons/<id>/` | конструктор урока: настройки, блоки, готовность к публикации |
| POST | `/api/panel/lessons/<id>/publish/` | опубликовать (только если все пункты готовности выполнены; иначе 400 `{detail, readiness}`, `ok` — `true`/`false`) |
| POST / DELETE | `/api/panel/lessons/<id>/blocks/…` | добавить или удалить блок `cards`, `grammar`, `text`, `quiz`; `reorder/` — порядок |
| GET / POST | `/api/panel/lessons/<id>/words/` | карточки урока; новая карточка |
| PATCH / DELETE | `/api/panel/words/<id>/` | изменить или удалить карточку |
| POST | `/api/panel/lessons/<id>/words/bulk/` | `{ids, action: publish \| delete}` |
| POST | `/api/panel/lessons/<id>/words/import/` | `{csv}` — строки `kz;ru;part_of_speech;example_kz;example_ru` |
| GET / PUT | `/api/panel/lessons/<id>/grammar/` | правило, таблица форм, примеры |
| GET / PUT | `/api/panel/lessons/<id>/text-quiz/` | текст для чтения и вопросы теста |
| POST | `/api/panel/media/` | загрузка картинки для карточки (multipart, поле `file`) |

Готовность урока к публикации: название по-русски, не меньше 10 карточек, у грамматики есть объяснение и пример, есть текст, у каждого вопроса теста отмечен правильный ответ.

## API

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/levels/` | уровни A1–C1 (`available` — открыт ли) |
| GET | `/api/levels/b2/modules/` | список модулей уровня |
| GET | `/api/levels/b2/content/` | весь контент уровня одним запросом (так грузит фронтенд) |
| GET | `/api/modules/<id>/` | модуль: слова, грамматика, текст, вопросы (без правильных ответов) |
| POST | `/api/modules/<id>/quiz/` | `{answers: [0,2,1,...]}` → результат, правильные ответы, баллы |
| GET | `/api/cards/review/?size=20` | колода «Повторение» из пройденных тем, трудные слова чаще |
| POST | `/api/cards/answer/` | `{word_id, result: "learned" \| "again"}` |
| POST | `/api/cards/complete/` | `{module_id}` — тема пройдена (`null` — повторение) |
| POST | `/api/topics/read/` | `{module_id, section: "words" \| "grammar" \| "text"}` |
| GET / PATCH | `/api/progress/` | прогресс; PATCH `{name, level}` |
| POST | `/api/progress/reset/` | сбросить прогресс |
| GET | `/api/leaderboard/` | топ‑50 по баллам |

Все запросы (кроме контента) требуют заголовок `X-Device-Id` или `Authorization: Token <key>`.

## Баллы

«Я выучил» +10, «Учить ещё раз» +2, тема впервые +30, повтор +10, тест +5 за каждый правильный ответ сверх лучшего результата. Меняются в `learning/services.py` (`POINTS`) — и в `frontend/src/store/progress.jsx`, пока фронт считает локально.

## Перед продакшеном

Задайте переменные окружения `DJANGO_SECRET_KEY` и `DJANGO_DEBUG=0`, сузьте `ALLOWED_HOSTS` и `CORS_ALLOWED_ORIGINS` в `config/settings.py`, перейдите на PostgreSQL.
