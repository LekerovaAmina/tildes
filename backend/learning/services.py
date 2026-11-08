"""Баллы, ранги, серия дней и колода повторения — те же правила, что во фронтенде
(frontend/src/store/progress.jsx и srs.js)."""

import random
from datetime import timedelta

from django.db.models import F
from django.utils import timezone

from .models import PointTransaction, Status, User, UserActivityDay

POINTS = {
    'learned': 10,  # «Я выучил»
    'again': 2,  # «Учить ещё раз»
    'topic_first': 30,  # тема карточек пройдена впервые
    'topic_repeat': 10,  # повторное прохождение / режим «Повторение»
    'quiz_correct': 5,  # за каждый правильный ответ сверх лучшего результата
}

REVIEW_SIZE = 20

# Ответы на карточки, пришедшие с перерывом меньше этого, считаются одной сессией
SESSION_GAP = timedelta(hours=2)

RANKS = [
    (0, 'Бастаушы', 'Новичок'),
    (150, 'Үйренуші', 'Ученик'),
    (500, 'Білгір', 'Знаток'),
    (1200, 'Шебер', 'Мастер'),
    (2500, 'Шешен', 'Оратор'),
]


def rank_of(points):
    current = RANKS[0]
    nxt = None
    for i, r in enumerate(RANKS):
        if points >= r[0]:
            current = r
            nxt = RANKS[i + 1] if i + 1 < len(RANKS) else None
    return {
        'title': current[1],
        'ru': current[2],
        'next': nxt[1] if nxt else None,
        'to_next': nxt[0] - points if nxt else 0,
    }


# ---------- Пользователь устройства ----------

def device_email(device_id):
    return f'{device_id.lower()}@{User.DEVICE_EMAIL_DOMAIN}'


def user_for_device(device_id):
    """MVP без регистрации: id устройства превращается в пользователя с техническим email."""
    email = device_email(device_id)
    user = User.objects.filter(email=email).first()
    if user is None:
        user = User.objects.create_user(email)  # без пароля — войти в админку им нельзя
    return user


# ---------- Баллы и активность ----------

def award(user, amount, reason, source=None):
    """Записывает начисление в point_transactions и увеличивает users.points."""
    if amount:
        PointTransaction.objects.create(
            user=user,
            amount=amount,
            reason=reason,
            source_type=_source_type(source),
            source_id=source.pk if source is not None else None,
        )
        User.objects.filter(pk=user.pk).update(points=F('points') + amount)
        user.refresh_from_db(fields=['points'])
    touch_activity(user)
    return amount


def _source_type(source):
    if source is None:
        return ''
    table = source._meta.db_table  # card_answers → card_answer
    return table[:-1] if table.endswith('s') else table


def touch_activity(user):
    UserActivityDay.objects.get_or_create(user=user, day=timezone.localdate())


def active_days(user, limit=60):
    days = user.activity_days.order_by('-day').values_list('day', flat=True)[:limit]
    return sorted(d.isoformat() for d in days)


def streak_of(days):
    s = set(days)
    d = timezone.localdate()
    if d.isoformat() not in s:
        d -= timedelta(days=1)
    n = 0
    while d.isoformat() in s:
        n += 1
        d -= timedelta(days=1)
    return n


# ---------- Публикация ----------

def published(qs):
    return qs.filter(status=Status.PUBLISHED)


# ---------- Колода повторения ----------

def weight_of(progress):
    """Новое слово = 1; каждое «ещё раз» +2; каждое «выучил» −0.5; минимум 0.3."""
    if progress is None:
        return 1.0
    return max(0.3, 1 + progress.again_count * 2 - progress.learned_count * 0.5)


def build_review_deck(words, progress_by_word, size=REVIEW_SIZE):
    """Взвешенная выборка без возвращения: трудные слова попадают чаще."""
    keyed = [(random.random() ** (1 / weight_of(progress_by_word.get(w.id))), w) for w in words]
    keyed.sort(key=lambda x: x[0], reverse=True)
    return [w for _, w in keyed[:size]]


def is_hard(progress):
    return progress is not None and progress.again_count >= 2 and progress.again_count >= progress.learned_count
