from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from . import services
from .models import CompletedTopic, Learner, Level, Module, QuizResult, TopicRead, Word, WordStat
from .serializers import (
    CardAnswerSerializer,
    CardCompleteSerializer,
    LevelSerializer,
    ModuleDetailSerializer,
    ModuleShortSerializer,
    ProfileUpdateSerializer,
    QuizSubmitSerializer,
    ReadSerializer,
    WordSerializer,
)


def get_learner(request):
    """MVP без регистрации: фронтенд генерирует id устройства и шлёт его в X-Device-Id."""
    device_id = request.headers.get('X-Device-Id', '').strip()
    if not device_id:
        raise ValidationError({'detail': 'Нужен заголовок X-Device-Id'})
    learner, _ = Learner.objects.get_or_create(device_id=device_id[:64])
    return learner


def validated(serializer_class, request):
    s = serializer_class(data=request.data)
    s.is_valid(raise_exception=True)
    return s.validated_data


# ---------- Контент ----------

@api_view(['GET'])
def levels(request):
    return Response(LevelSerializer(Level.objects.all(), many=True).data)


@api_view(['GET'])
def level_modules(request, code):
    level = get_object_or_404(Level, code=code.upper())
    return Response(ModuleShortSerializer(level.modules.all(), many=True).data)


@api_view(['GET'])
def level_content(request, code):
    """Весь контент уровня одним запросом — фронтенд грузит его при старте."""
    level = get_object_or_404(Level, code=code.upper())
    modules = level.modules.prefetch_related('words', 'questions')
    return Response({'level': LevelSerializer(level).data, 'modules': ModuleDetailSerializer(modules, many=True).data})


@api_view(['GET'])
def module_detail(request, pk):
    module = get_object_or_404(Module.objects.prefetch_related('words', 'questions'), pk=pk)
    return Response(ModuleDetailSerializer(module).data)


# ---------- Карточки ----------

@api_view(['GET'])
def cards_review(request):
    """Колода «Повторение»: слова из пройденных тем, трудные — чаще."""
    learner = get_learner(request)
    size = min(int(request.query_params.get('size', services.REVIEW_SIZE)), 100)
    words = list(Word.objects.filter(module__completedtopic__learner=learner).select_related('module'))
    stats = {s.word_id: s for s in learner.word_stats.filter(word__in=words)}
    deck = services.build_review_deck(words, stats, size)
    data = WordSerializer(deck, many=True).data
    for item in data:
        item['hard'] = services.is_hard(stats.get(item['id']))
    return Response(data)


@api_view(['POST'])
@transaction.atomic
def cards_answer(request):
    learner = get_learner(request)
    data = validated(CardAnswerSerializer, request)
    word = get_object_or_404(Word, pk=data['word_id'])
    stat, _ = WordStat.objects.get_or_create(learner=learner, word=word)
    setattr(stat, data['result'], F(data['result']) + 1)
    stat.save()
    stat.refresh_from_db()

    gained = services.POINTS[data['result']]
    learner.points += gained
    services.touch_activity(learner)
    learner.save()
    return Response({'gained': gained, 'points': learner.points, 'learned': stat.learned, 'again': stat.again})


@api_view(['POST'])
@transaction.atomic
def cards_complete(request):
    learner = get_learner(request)
    module_id = validated(CardCompleteSerializer, request).get('module_id')
    first = False
    if module_id is not None:
        module = get_object_or_404(Module, pk=module_id)
        _, first = CompletedTopic.objects.get_or_create(learner=learner, module=module)
    gained = services.POINTS['topic_first' if first else 'topic_repeat']
    learner.points += gained
    services.touch_activity(learner)
    learner.save()
    return Response({'gained': gained, 'points': learner.points, 'first': first})


# ---------- Темы ----------

@api_view(['POST'])
@transaction.atomic
def quiz_submit(request, pk):
    learner = get_learner(request)
    module = get_object_or_404(Module, pk=pk)
    answers = validated(QuizSubmitSerializer, request)['answers']
    questions = list(module.questions.all())
    results = [
        {'question_id': q.id, 'correct_answer': q.answer, 'is_correct': i < len(answers) and answers[i] == q.answer}
        for i, q in enumerate(questions)
    ]
    correct = sum(r['is_correct'] for r in results)

    qr, _ = QuizResult.objects.get_or_create(learner=learner, module=module)
    gained = max(0, correct - qr.best) * services.POINTS['quiz_correct']
    qr.best = max(qr.best, correct)
    qr.save()
    learner.points += gained
    services.touch_activity(learner)
    learner.save()
    return Response({
        'correct': correct, 'total': len(questions), 'best': qr.best,
        'gained': gained, 'points': learner.points, 'results': results,
    })


@api_view(['POST'])
def topic_read(request):
    learner = get_learner(request)
    data = validated(ReadSerializer, request)
    module = get_object_or_404(Module, pk=data['module_id'])
    TopicRead.objects.update_or_create(learner=learner, module=module, defaults={data['section']: True})
    return Response({'ok': True})


# ---------- Прогресс и рейтинг ----------

@api_view(['GET', 'PATCH'])
def progress(request):
    """Формат повторяет состояние фронтенда (src/store/progress.jsx)."""
    learner = get_learner(request)

    if request.method == 'PATCH':
        data = validated(ProfileUpdateSerializer, request)
        if 'name' in data:
            learner.name = data['name']
        if 'level' in data:
            learner.level = get_object_or_404(Level, code=data['level'].upper())
        learner.save()

    reads = {
        r.module_id: {'words': r.words, 'grammar': r.grammar, 'text': r.text}
        for r in learner.topic_reads.all()
    }
    return Response({
        'name': learner.name,
        'level': learner.level_id,
        'points': learner.points,
        'rank': services.rank_of(learner.points),
        'streak': services.streak_of(learner.active_days),
        'activeDays': learner.active_days,
        'wordStats': {s.word_id: {'learned': s.learned, 'again': s.again} for s in learner.word_stats.all()},
        'completedCardTopics': list(learner.completed_topics.values_list('module_id', flat=True)),
        'quizBest': {q.module_id: q.best for q in learner.quiz_results.all()},
        'readTopics': reads,
    })


@api_view(['POST'])
def progress_reset(request):
    learner = get_learner(request)
    learner.word_stats.all().delete()
    learner.completed_topics.all().delete()
    learner.quiz_results.all().delete()
    learner.topic_reads.all().delete()
    learner.points = 0
    learner.active_days = []
    learner.save()
    return Response({'ok': True})


@api_view(['GET'])
def leaderboard(request):
    device_id = request.headers.get('X-Device-Id', '')
    top = Learner.objects.order_by('-points', 'created_at')[:50]
    return Response([
        {'place': i + 1, 'name': l.name or 'Аноним', 'points': l.points, 'me': l.device_id == device_id}
        for i, l in enumerate(top)
    ])
