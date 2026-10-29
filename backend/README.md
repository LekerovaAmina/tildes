# Tildes — бэкенд (Python + Django)

Django 5.1 + Django REST Framework + django-cors-headers, база SQLite.
Все пакеты уже скачаны в папку `wheels/` — установка работает **без интернета**.

## Установка

Нужен Python 3.10+ (`python --version`).

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
pip install --no-index --find-links wheels -r requirements.txt
python manage.py migrate
python manage.py load_content
python manage.py runserver 8000
```

- API: http://127.0.0.1:8000/api/levels/
- Админка (редактирование слов, тем, вопросов): http://127.0.0.1:8000/admin/ — сначала `python manage.py createsuperuser`
- Тесты: `python manage.py test learning`

## Структура

```
backend/
├── config/            настройки Django (settings.py, urls.py)
├── learning/          приложение
│   ├── models.py      Level, Module, Word, Question + прогресс: Learner, WordStat, CompletedTopic, QuizResult, TopicRead
│   ├── services.py    баллы, ранги, серия дней, взвешенная колода повторения
│   ├── views.py       API
│   ├── urls.py        маршруты /api/...
│   ├── admin.py       админка
│   ├── data/content.json                    контент B2 (10 модулей, 225 слов, 50 вопросов)
│   └── management/commands/load_content.py  загрузка/обновление контента
├── wheels/            скачанные пакеты (Django, DRF, CORS и зависимости)
├── requirements.txt
└── setup.bat / setup.sh / run.bat / run.sh
```

## Пользователь

Регистрации пока нет. Фронтенд генерирует id устройства и отправляет его в заголовке `X-Device-Id` — по нему создаётся `Learner`. Позже можно добавить авторизацию и связать `Learner` с `User`.

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

Все запросы (кроме контента) требуют заголовок `X-Device-Id`.

## Баллы

«Я выучил» +10, «Учить ещё раз» +2, тема впервые +30, повтор +10, тест +5 за каждый правильный ответ сверх лучшего результата. Меняются в `learning/services.py` (`POINTS`) — и в `frontend/src/store/progress.jsx`, пока фронт считает локально.

## Перед продакшеном

Задайте переменные окружения `DJANGO_SECRET_KEY` и `DJANGO_DEBUG=0`, сузьте `ALLOWED_HOSTS` и `CORS_ALLOWED_ORIGINS` в `config/settings.py`, перейдите на PostgreSQL.
