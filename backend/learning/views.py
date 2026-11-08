from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from . import services
from .models import (
    CardAnswer,
    CardResult,
    CardSession,
    Level,
    Module,
    PointTransaction,
    QuizAttempt,
    QuizAttemptAnswer,
    User,
    UserLessonProgress,
    UserWordProgress,
    Word,
)
from .serializers import (
    CardAnswerSerializer,
    CardCompleteSerializer,
    ProfileUpdateSerializer,
    QuizSubmitSerializer,
    ReadSerializer,
    level_data,
    module_detail as module_detail_data,
    module_quiz,
    module_short,
    modules_with_content,
    word_data,
)

READ_FIELDS = {'words': 'words_read', 'grammar': 'grammar_read', 'text': 'text_read'}


def get_user(request):
    """MVP без регистрации: фронтенд генерирует id устройства и шлёт его в X-Device-Id."""
    device_id = request.headers.get('X-Device-Id', '').strip()
    if not device_id:
        raise ValidationError({'detail': 'Нужен заголовок X-Device-Id'})
    return services.user_for_device(device_id[:64])


def validated(serializer_class, request):
    s = serializer_class(data=request.data)
    s.is_valid(raise_exception=True)
    return s.validated_data


def get_module(pk):
    module = modules_with_content(Module.objects.filter(pk=pk)).first()
    if module is None:
        raise NotFound('Тема не найдена')
    return module


def lesson_with(module, relation):
    """Урок темы, в котором лежит этот раздел (слова, грамматика, текст, тест); иначе — первый урок."""
    lessons = list(module.lessons.all())
    for lesson in lessons:
        if list(getattr(lesson, relation).all()):
            return lesson
    if not lessons:
        raise NotFound('В теме нет уроков')
    return lessons[0]


def lesson_progress(user, lesson):
    return UserLessonProgress.objects.select_for_update().get_or_create(user=user, lesson=lesson)[0]


# ---------- Контент ----------

@api_view(['GET'])
def levels(request):
    return Response([level_data(lv) for lv in Level.objects.all()])


@api_view(['GET'])
def level_modules(request, code):
    level = get_object_or_404(Level, code=code.upper())
    return Response([module_short(m) for m in modules_with_content(level.modules.all())])


@api_view(['GET'])
def level_content(request, code):
    """Весь контент уровня одним запросом — фронтенд грузит его при старте."""
    level = get_object_or_404(Level, code=code.upper())
    modules = modules_with_content(level.modules.all())
    return Response({'level': level_data(level), 'modules': [module_detail_data(m) for m in modules]})


@api_view(['GET'])
def module_detail(request, pk):
    return Response(module_detail_data(get_module(pk)))


# ---------- Карточки ----------

def open_session(user):
    """Текущая незавершённая сессия карточек (ответы с перерывом меньше SESSION_GAP) или новая."""
    session = (
        CardSession.objects.select_for_update()
        .filter(user=user, finished_at__isnull=True)
        .order_by('-started_at')
        .first()
    )
    if session is not None:
        last = session.answers.order_by('-answered_at').values_list('answered_at', flat=True).first()
        if (last or session.started_at) >= timezone.now() - services.SESSION_GAP:
            return session
    return CardSession.objects.create(user=user)


@api_view(['GET'])
def cards_review(request):
    """Колода «Повторение»: слова из пройденных тем, трудные — чаще."""
    user = get_user(request)
    try:
        size = max(1, min(int(request.query_params.get('size', services.REVIEW_SIZE)), 100))
    except ValueError:
        raise ValidationError({'size': 'Нужно число'})
    module_ids = completed_modules(user)
    words = list(
        services.published(Word.objects)
        .filter(lesson__module_id__in=module_ids, lesson__status='published', lesson__module__status='published')
        .select_related('lesson')
    )
    progress = {p.word_id: p for p in user.word_progress.filter(word__in=words)}
    deck = services.build_review_deck(words, progress, size)
    return Response([
        {**word_data(w, w.lesson.module_id), 'hard': services.is_hard(progress.get(w.id))} for w in deck
    ])


@api_view(['POST'])
@transaction.atomic
def cards_answer(request):
    user = get_user(request)
    data = validated(CardAnswerSerializer, request)
    word = get_object_or_404(Word, pk=data['word_id'])
    result = data['result']

    wp, _ = UserWordProgress.objects.select_for_update().get_or_create(user=user, word=word)
    counter = 'learned_count' if result == CardResult.LEARNED else 'again_count'
    setattr(wp, counter, getattr(wp, counter) + 1)
    wp.last_result = result
    wp.last_seen_at = timezone.now()
    wp.save()

    session = open_session(user)
    answer = CardAnswer.objects.create(session=session, word=word, result=result)
    gained = services.award(
        user, services.POINTS[result],
        PointTransaction.Reason.CARD_LEARNED if result == CardResult.LEARNED else PointTransaction.Reason.CARD_AGAIN,
        answer,
    )
    CardSession.objects.filter(pk=session.pk).update(
        cards_total=F('cards_total') + 1,
        points_earned=F('points_earned') + gained,
        **{counter: F(counter) + 1},
    )
    return Response({'gained': gained, 'points': user.points, 'learned': wp.learned_count, 'again': wp.again_count})


@api_view(['POST'])
@transaction.atomic
def cards_complete(request):
    user = get_user(request)
    module_id = validated(CardCompleteSerializer, request).get('module_id')
    session = open_session(user)
    first = False

    if module_id is not None:
        module = get_module(module_id)
        lesson = lesson_with(module, 'words')
        lp = lesson_progress(user, lesson)
        first = lp.first_completed_at is None
        lp.cards_completions += 1
        if first:
            lp.first_completed_at = timezone.now()
        lp.save()
        session.mode, session.module, session.lesson = CardSession.Mode.TOPIC, module, lesson
    else:
        session.mode = CardSession.Mode.REVIEW

    gained = services.award(
        user, services.POINTS['topic_first' if first else 'topic_repeat'],
        PointTransaction.Reason.TOPIC_FIRST if first else PointTransaction.Reason.TOPIC_REPEAT,
        session,
    )
    session.refresh_from_db(fields=['cards_total', 'learned_count', 'again_count', 'points_earned'])
    session.points_earned += gained
    session.finished_at = timezone.now()
    session.save()
    return Response({'gained': gained, 'points': user.points, 'first': first})


# ---------- Темы ----------

@api_view(['POST'])
@transaction.atomic
def quiz_submit(request, pk):
    user = get_user(request)
    module = get_module(pk)
    quiz = module_quiz(module)
    if quiz is None:
        raise NotFound('У темы нет теста')
    answers = validated(QuizSubmitSerializer, request)['answers']
    questions = list(quiz.questions.all())

    attempt = QuizAttempt.objects.create(user=user, quiz=quiz, total_count=len(questions))
    results, rows = [], []
    for i, q in enumerate(questions):
        options = list(q.options.all())
        correct_index = next((j for j, o in enumerate(options) if o.is_correct), None)
        chosen = answers[i] if i < len(answers) else None
        option = options[chosen] if chosen is not None and 0 <= chosen < len(options) else None
        is_correct = option is not None and option.is_correct
        rows.append(QuizAttemptAnswer(attempt=attempt, question=q, option=option, is_correct=is_correct))
        results.append({'question_id': q.id, 'correct_answer': correct_index, 'is_correct': is_correct})
    QuizAttemptAnswer.objects.bulk_create(rows)
    correct = sum(r['is_correct'] for r in results)

    lp = lesson_progress(user, quiz.lesson)
    gained = max(0, correct - lp.quiz_best) * services.POINTS['quiz_correct']
    lp.quiz_best = max(lp.quiz_best, correct)
    lp.save()

    attempt.correct_count, attempt.points_earned = correct, gained
    attempt.save(update_fields=['correct_count', 'points_earned'])
    services.award(user, gained, PointTransaction.Reason.QUIZ, attempt)
    return Response({
        'correct': correct, 'total': len(questions), 'best': lp.quiz_best,
        'gained': gained, 'points': user.points, 'results': results,
    })


@api_view(['POST'])
@transaction.atomic
def topic_read(request):
    user = get_user(request)
    data = validated(ReadSerializer, request)
    module = get_module(data['module_id'])
    relation = {'words': 'words', 'grammar': 'grammar_rules', 'text': 'texts'}[data['section']]
    lp = lesson_progress(user, lesson_with(module, relation))
    setattr(lp, READ_FIELDS[data['section']], True)
    lp.save()
    return Response({'ok': True})


# ---------- Прогресс и рейтинг ----------

def completed_modules(user):
    return list(
        user.lesson_progress.filter(cards_completions__gt=0)
        .values_list('lesson__module_id', flat=True).distinct()
    )


@api_view(['GET', 'PATCH'])
def progress(request):
    """Формат повторяет состояние фронтенда (src/store/progress.jsx)."""
    user = get_user(request)

    if request.method == 'PATCH':
        data = validated(ProfileUpdateSerializer, request)
        if 'name' in data:
            user.display_name = data['name']
        if 'level' in data:
            user.current_level = get_object_or_404(Level, code=data['level'].upper())
        user.save(update_fields=['display_name', 'current_level'])

    quiz_best, reads, completed = {}, {}, set()
    for lp in user.lesson_progress.select_related('lesson'):
        mid = lp.lesson.module_id
        if lp.cards_completions:
            completed.add(mid)
        if lp.quiz_best:
            quiz_best[mid] = max(quiz_best.get(mid, 0), lp.quiz_best)
        r = reads.setdefault(mid, {'words': False, 'grammar': False, 'text': False})
        r['words'] |= lp.words_read
        r['grammar'] |= lp.grammar_read
        r['text'] |= lp.text_read
    reads = {mid: r for mid, r in reads.items() if any(r.values())}

    days = services.active_days(user)
    return Response({
        'name': user.display_name,
        'level': user.current_level.code if user.current_level else None,
        'points': user.points,
        'rank': services.rank_of(user.points),
        'streak': services.streak_of(days),
        'activeDays': days,
        'wordStats': {
            p.word_id: {'learned': p.learned_count, 'again': p.again_count} for p in user.word_progress.all()
        },
        'completedCardTopics': sorted(completed),
        'quizBest': quiz_best,
        'readTopics': reads,
    })


@api_view(['POST'])
@transaction.atomic
def progress_reset(request):
    user = get_user(request)
    for related in (
        user.word_progress, user.lesson_progress, user.card_sessions,
        user.quiz_attempts, user.point_transactions, user.activity_days,
    ):
        related.all().delete()
    user.points = 0
    user.save(update_fields=['points'])
    return Response({'ok': True})


@api_view(['GET'])
def leaderboard(request):
    device_id = request.headers.get('X-Device-Id', '').strip()[:64]
    my_email = services.device_email(device_id) if device_id else None
    top = User.objects.filter(is_active=True, role=User.Role.STUDENT).order_by('-points', 'date_joined')[:50]
    return Response([
        {'place': i + 1, 'name': u.display_name or 'Аноним', 'points': u.points, 'me': u.email == my_email}
        for i, u in enumerate(top)
    ])
