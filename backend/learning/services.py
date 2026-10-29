"""Баллы и интервальное повторение — те же правила, что во фронтенде
(frontend/src/store/progress.jsx и srs.js)."""

import random
from datetime import date

POINTS = {
    'learned': 10,  # «Я выучил»
    'again': 2,  # «Учить ещё раз»
    'topic_first': 30,  # тема карточек пройдена впервые
    'topic_repeat': 10,  # повторное прохождение / режим «Повторение»
    'quiz_correct': 5,  # за каждый правильный ответ сверх лучшего результата
}

REVIEW_SIZE = 20

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


def touch_activity(learner):
    today = date.today().isoformat()
    if today not in learner.active_days:
        learner.active_days = (learner.active_days + [today])[-60:]


def streak_of(days):
    s = set(days)
    d = date.today()
    if d.isoformat() not in s:
        d = date.fromordinal(d.toordinal() - 1)
    n = 0
    while d.isoformat() in s:
        n += 1
        d = date.fromordinal(d.toordinal() - 1)
    return n


def weight_of(stat):
    """Новое слово = 1; каждое «ещё раз» +2; каждое «выучил» −0.5; минимум 0.3."""
    if stat is None:
        return 1.0
    return max(0.3, 1 + stat.again * 2 - stat.learned * 0.5)


def build_review_deck(words, stats_by_word, size=REVIEW_SIZE):
    """Взвешенная выборка без возвращения: трудные слова попадают чаще."""
    keyed = [(random.random() ** (1 / weight_of(stats_by_word.get(w.id))), w) for w in words]
    keyed.sort(key=lambda x: x[0], reverse=True)
    return [w for _, w in keyed[:size]]


def is_hard(stat):
    return stat is not None and stat.again >= 2 and stat.again >= stat.learned
