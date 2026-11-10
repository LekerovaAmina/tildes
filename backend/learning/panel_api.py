"""API админ-панели сайта (/panel на фронтенде, макет Figma «Tildes — админ-панель»).

Все запросы — только для сотрудников (роль admin или editor, users.is_staff) с заголовком
Authorization: Token <key>. Изменения пишутся в audit_log так же, как в Django-админке.

В интерфейсе у урока четыре блока: «Карточки слов» (cards), «Грамматика», «Текст», «Тест».
В базе блок карточек — это две строки lesson_blocks (words и cards), их создаём и удаляем вместе.
"""

import csv
import io
from datetime import timedelta

from django.db import connection, transaction
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, parser_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from .admin import write_audit
from .management.commands.load_content import sync_ordered
from .models import (
    AuditLog,
    GrammarExample,
    GrammarRule,
    GrammarTableRow,
    Lesson,
    LessonBlock,
    Level,
    MediaFile,
    Module,
    Quiz,
    QuizOption,
    QuizQuestion,
    Status,
    Text,
    User,
    UserActivityDay,
    Word,
)

PUBLISHED = Status.PUBLISHED
LESSON_LETTERS = 'АӘБВГҒДЕЖЗИЙК'

# Блок интерфейса → строки lesson_blocks
UI_BLOCKS = {
    'cards': [LessonBlock.Type.WORDS, LessonBlock.Type.CARDS],
    'grammar': [LessonBlock.Type.GRAMMAR],
    'text': [LessonBlock.Type.TEXT],
    'quiz': [LessonBlock.Type.QUIZ],
}
DB_TO_UI = {LessonBlock.Type.WORDS: 'cards', LessonBlock.Type.CARDS: 'cards', LessonBlock.Type.GRAMMAR: 'grammar',
            LessonBlock.Type.TEXT: 'text', LessonBlock.Type.QUIZ: 'quiz'}
MIN_CARDS = 10


class IsStaff(BasePermission):
    message = 'Админ-панель доступна только администраторам и редакторам.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


def panel(methods, parsers=None):
    """api_view + вход по токену + доступ только сотрудникам."""
    def wrap(fn):
        fn = permission_classes([IsStaff])(fn)
        fn = authentication_classes([TokenAuthentication])(fn)
        if parsers:
            fn = parser_classes(parsers)(fn)
        return api_view(methods)(fn)
    return wrap


def audit(request, action, obj, **extra):
    write_audit(request.user, action, obj, {'repr': str(obj)[:200], **extra})


def require(data, *fields):
    missing = [f for f in fields if not str(data.get(f, '')).strip()]
    if missing:
        raise ValidationError({f: 'Обязательное поле' for f in missing})


def set_status(obj, value):
    if value not in Status.values:
        raise ValidationError({'status': 'Неизвестный статус'})
    obj.status = value
    if value == PUBLISHED and hasattr(obj, 'published_at') and obj.published_at is None:
        obj.published_at = timezone.now()


# =====================================================================
#  Представления
# =====================================================================

def lesson_letter(lesson):
    return LESSON_LETTERS[lesson.sort_order] if lesson.sort_order < len(LESSON_LETTERS) else str(lesson.sort_order + 1)


def lesson_blocks(lesson):
    """Блоки урока в порядке прохождения: ['cards', 'grammar', ...]."""
    seen = []
    for b in sorted(lesson.blocks.all(), key=lambda b: b.sort_order):
        ui = DB_TO_UI.get(b.block_type)
        if ui and b.is_enabled and ui not in seen:
            seen.append(ui)
    return seen


def level_data(level, module_count=None):
    return {
        'code': level.code,
        'title_kz': level.title_kz,
        'title_ru': level.title_ru,
        'description': level.description,
        'is_published': level.is_published,
        'module_count': level.modules.count() if module_count is None else module_count,
    }


def lesson_short(lesson):
    return {
        'id': lesson.id,
        'code': lesson.code,
        'letter': lesson_letter(lesson),
        'title_kz': lesson.title_kz,
        'title_ru': lesson.title_ru,
        'status': lesson.status,
        'blocks': lesson_blocks(lesson),
    }


def module_data(module):
    lessons = sorted(module.lessons.all(), key=lambda l: l.sort_order)
    rule = GrammarRule.objects.filter(lesson__module=module).order_by('lesson__sort_order', 'sort_order').first()
    return {
        'id': module.id,
        'number': module.number,
        'title_kz': module.title_kz,
        'title_ru': module.title_ru,
        'emoji': module.emoji,
        'color': module.color,
        'status': module.status,
        'lesson_count': len(lessons),
        'word_count': Word.objects.filter(lesson__module=module).count(),
        'grammar_title': rule.title_kz if rule else '',
        'lessons': [lesson_short(l) for l in lessons],
    }


def where(lesson):
    m = lesson.module
    return f'{m.level.code} · Модуль {m.number} · Урок {lesson_letter(lesson)}'


def readiness(lesson):
    """Пункты «Готовность к публикации» из макета. ok=False — урок можно сохранить только черновиком."""
    blocks = lesson_blocks(lesson)
    words = lesson.words.count()
    rule = lesson.grammar_rules.first()
    text = lesson.texts.first()
    quiz = lesson.quizzes.first()
    questions = list(quiz.questions.prefetch_related('options')) if quiz else []
    items = [
        {'key': 'title_ru', 'ok': bool(lesson.title_ru.strip()),
         'label': 'Название по-русски' + ('' if lesson.title_ru.strip() else ' не заполнено')},
        {'key': 'cards', 'ok': 'cards' in blocks and words >= MIN_CARDS,
         'label': f'Карточки: минимум {MIN_CARDS} (сейчас {words})' if 'cards' in blocks else 'Карточки: блок не добавлен'},
        {'key': 'grammar', 'ok': 'grammar' in blocks and bool(rule and rule.explanation.strip() and rule.examples.exists()),
         'label': 'Грамматика: объяснение и пример' if 'grammar' in blocks else 'Грамматика: блок не добавлен'},
        {'key': 'text', 'ok': 'text' in blocks and bool(text and text.paragraphs),
         'label': 'Текст: заголовок и абзацы' if 'text' in blocks else 'Текст: блок не добавлен'},
        {'key': 'quiz', 'ok': 'quiz' in blocks and bool(questions) and all(
            any(o.is_correct for o in q.options.all()) for q in questions),
         'label': f'Тест: вопросов {len(questions)}, у каждого отмечен ответ' if 'quiz' in blocks else 'Тест: блок не добавлен'},
    ]
    return {'items': items, 'ok': all(i['ok'] for i in items)}


def plural(n, one, few, many):
    """1 карточка, 2 карточки, 5 карточек."""
    if n % 10 == 1 and n % 100 != 11:
        return f'{n} {one}'
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return f'{n} {few}'
    return f'{n} {many}'


def block_summary(lesson, block):
    if block == 'cards':
        return plural(lesson.words.count(), 'карточка', 'карточки', 'карточек')
    if block == 'grammar':
        rule = lesson.grammar_rules.first()
        return rule.title_kz if rule else 'Правило не заполнено'
    if block == 'text':
        text = lesson.texts.first()
        return text.title if text else 'Текст не заполнен'
    quiz = lesson.quizzes.first()
    return plural(quiz.questions.count(), 'вопрос', 'вопроса', 'вопросов') if quiz else 'Вопросов пока нет'


def lesson_detail(lesson):
    module = lesson.module
    blocks = lesson_blocks(lesson)
    siblings = list(module.lessons.order_by('sort_order'))
    return {
        **lesson_short(lesson),
        'module': {'id': module.id, 'number': module.number, 'title_kz': module.title_kz},
        'level': {'code': module.level.code, 'title_kz': module.level.title_kz},
        'where': where(lesson),
        'position': siblings.index(lesson) if lesson in siblings else 0,
        'positions': [f'Урок {lesson_letter(l)} ({i + 1})' for i, l in enumerate(siblings)],
        'blocks': [{'type': b, 'summary': block_summary(lesson, b)} for b in blocks],
        'readiness': readiness(lesson),
        'updated_at': lesson.updated_at,
    }


def lesson_head(lesson):
    """Шапка редакторов карточек, грамматики и текста: где урок лежит."""
    return lesson_short(lesson) | {
        'where': where(lesson),
        'module_id': lesson.module_id,
        'module_number': lesson.module.number,
        'level_code': lesson.module.level.code,
    }


def word_data(w):
    return {
        'id': w.id,
        'kz': w.kz,
        'ru': w.ru,
        'transcription': w.transcription,
        'part_of_speech': w.part_of_speech,
        'example_kz': w.example_kz,
        'example_ru': w.example_ru,
        'status': w.status,
        'image': {'id': w.image_id, 'url': w.image.file.url} if w.image_id else None,
        'has_audio': bool(w.audio_id),
    }


# =====================================================================
#  Дашборд и поиск
# =====================================================================

@panel(['GET'])
def dashboard(request):
    code = request.query_params.get('level', 'B2').upper()
    lessons = Lesson.objects.filter(module__level__code=code)
    stats = {
        'modules': Module.objects.filter(level__code=code).count(),
        'lessons': lessons.count(),
        'words': Word.objects.filter(lesson__module__level__code=code).count(),
        'questions': QuizQuestion.objects.filter(quiz__lesson__module__level__code=code).count(),
    }

    coverage = []
    for lv in Level.objects.annotate(
        total=Count('modules', distinct=True),
        published=Count('modules', filter=Q(modules__status=PUBLISHED), distinct=True),
    ):
        coverage.append({**level_data(lv, lv.total), 'published_modules': lv.published})

    drafts = [
        {'id': l.id, 'title_kz': l.title_kz, 'where': where(l), 'status': l.status}
        for l in Lesson.objects.exclude(status=PUBLISHED).select_related('module__level').order_by('-updated_at')[:5]
    ]

    students = User.objects.filter(role=User.Role.STUDENT, is_active=True)
    today = timezone.localdate()
    active = lambda days: UserActivityDay.objects.filter(  # noqa: E731
        user__in=students, day__gt=today - timedelta(days=days)).values('user').distinct().count()
    activity = {
        'students': students.exclude(email__endswith='@' + User.DEVICE_EMAIL_DOMAIN).count(),
        'anonymous': students.filter(email__endswith='@' + User.DEVICE_EMAIL_DOMAIN).count(),
        'active_today': active(1),
        'active_week': active(7),
        'top': [
            {'name': u.display_name or u.email.split('@')[0], 'points': u.points}
            for u in students.exclude(email__endswith='@' + User.DEVICE_EMAIL_DOMAIN).order_by('-points')[:5]
        ],
    }

    recent = []
    for a in AuditLog.objects.select_related('actor')[:8]:
        recent.append({
            'id': a.id,
            'action': a.action,
            'action_label': a.get_action_display(),
            'entity_type': a.entity_type,
            'what': a.changes.get('repr') or f'{a.entity_type} #{a.entity_id}',
            'where': a.changes.get('where', ''),
            'who': (a.actor.display_name or a.actor.email) if a.actor else 'система',
            'role': a.actor.role if a.actor else '',
            'when': a.created_at,
        })
    return Response({'level': code, 'stats': stats, 'coverage': coverage, 'drafts': drafts,
                     'activity': activity, 'recent': recent})


@panel(['GET'])
def search(request):
    q = request.query_params.get('q', '').strip()
    if len(q) < 2:
        return Response({'lessons': [], 'words': []})
    lessons = Lesson.objects.select_related('module__level')
    words = Word.objects.select_related('lesson__module__level')
    if connection.vendor == 'sqlite':
        # SQLite не умеет без учёта регистра для кириллицы — фильтруем в Python (данных немного)
        needle = q.casefold()
        lessons = [l for l in lessons if needle in f'{l.title_kz} {l.title_ru}'.casefold()][:8]
        words = [w for w in words if needle in f'{w.kz} {w.ru}'.casefold()][:8]
    else:
        lessons = lessons.filter(Q(title_kz__icontains=q) | Q(title_ru__icontains=q))[:8]
        words = words.filter(Q(kz__icontains=q) | Q(ru__icontains=q))[:8]
    return Response({
        'lessons': [{'id': l.id, 'title': l.title_kz, 'where': where(l)} for l in lessons],
        'words': [{'id': w.id, 'lesson_id': w.lesson_id, 'kz': w.kz, 'ru': w.ru, 'where': where(w.lesson)} for w in words],
    })


# =====================================================================
#  Уровни и модули
# =====================================================================

@panel(['GET', 'POST'])
def levels(request):
    if request.method == 'POST':
        d = request.data
        require(d, 'code', 'title_kz', 'title_ru')
        code = d['code'].strip().upper()[:4]
        if Level.objects.filter(code=code).exists():
            raise ValidationError({'code': 'Такой уровень уже есть'})
        order = (Level.objects.aggregate(m=Max('sort_order'))['m'] or 0) + 1
        level = Level.objects.create(code=code, title_kz=d['title_kz'], title_ru=d['title_ru'],
                                     description=d.get('description', ''), sort_order=order)
        audit(request, AuditLog.Action.CREATE, level, where=code)
        return Response(level_data(level), status=status.HTTP_201_CREATED)
    return Response([level_data(lv, lv.n) for lv in Level.objects.annotate(n=Count('modules'))])


@panel(['PATCH'])
def level_update(request, code):
    level = get_object_or_404(Level, code=code.upper())
    was_published = level.is_published
    for f in ('title_kz', 'title_ru', 'description'):
        if f in request.data:
            setattr(level, f, request.data[f])
    if 'is_published' in request.data:
        level.is_published = bool(request.data['is_published'])
    level.save()
    audit(request, AuditLog.Action.PUBLISH if level.is_published and not was_published else AuditLog.Action.UPDATE,
          level, where=level.code)
    return Response(level_data(level))


@panel(['GET', 'POST'])
def level_modules(request, code):
    level = get_object_or_404(Level, code=code.upper())
    if request.method == 'POST':
        d = request.data
        require(d, 'title_kz')
        number = (level.modules.aggregate(m=Max('number'))['m'] or 0) + 1
        module = Module.objects.create(
            level=level, number=number, sort_order=number, title_kz=d['title_kz'], title_ru=d.get('title_ru', ''),
            emoji=d.get('emoji', '📘')[:8], color=d.get('color') or '#8B5CF6', created_by=request.user,
        )
        audit(request, AuditLog.Action.CREATE, module, where=f'{level.code} · Модуль {number}')
        return Response(module_data(module), status=status.HTTP_201_CREATED)
    modules = level.modules.prefetch_related('lessons__blocks').order_by('sort_order', 'number')
    return Response({'level': level_data(level), 'modules': [module_data(m) for m in modules]})


@panel(['POST'])
@transaction.atomic
def modules_reorder(request, code):
    level = get_object_or_404(Level, code=code.upper())
    ids = [int(i) for i in request.data.get('ids', [])]
    by_id = {m.id: m for m in level.modules.all()}
    for i, mid in enumerate(ids):
        if mid in by_id:
            Module.objects.filter(pk=mid).update(sort_order=i + 1)
    return Response({'ok': True})


@panel(['PATCH'])
def module_update(request, pk):
    module = get_object_or_404(Module, pk=pk)
    before = module.status
    for f in ('title_kz', 'title_ru', 'emoji', 'color'):
        if f in request.data:
            setattr(module, f, request.data[f])
    if 'status' in request.data:
        set_status(module, request.data['status'])
    module.save()
    published = module.status == PUBLISHED and before != PUBLISHED
    audit(request, AuditLog.Action.PUBLISH if published else AuditLog.Action.UPDATE, module,
          where=f'{module.level.code} · Модуль {module.number}')
    return Response(module_data(module))


# =====================================================================
#  Урок (конструктор)
# =====================================================================

def free_code(module):
    used = set(module.lessons.values_list('code', flat=True))
    for n in range(1, 100):
        code = f'{module.number}.{n}'
        if code not in used and len(code) <= 4:
            return code
    raise ValidationError({'detail': 'В модуле слишком много уроков'})


def renumber(module, moving=None, position=None):
    lessons = [l for l in module.lessons.order_by('sort_order', 'id') if l != moving]
    if moving is not None:
        lessons.insert(max(0, min(position, len(lessons))), moving)
    for i, l in enumerate(lessons):
        if l.sort_order != i:
            Lesson.objects.filter(pk=l.pk).update(sort_order=i)
            l.sort_order = i


@panel(['POST'])
@transaction.atomic
def lesson_create(request, module_id):
    module = get_object_or_404(Module, pk=module_id)
    title = (request.data.get('title_kz') or 'Новый урок').strip()
    lesson = Lesson.objects.create(
        module=module, code=free_code(module), title_kz=title, title_ru=request.data.get('title_ru', ''),
        sort_order=module.lessons.count(), status=Status.DRAFT, created_by=request.user, updated_by=request.user,
    )
    audit(request, AuditLog.Action.CREATE, lesson, where=where(lesson))
    return Response(lesson_detail(lesson), status=status.HTTP_201_CREATED)


@panel(['GET', 'PATCH', 'DELETE'])
@transaction.atomic
def lesson(request, pk):
    lesson = get_object_or_404(Lesson.objects.select_related('module__level'), pk=pk)
    if request.method == 'DELETE':
        audit(request, AuditLog.Action.DELETE, lesson, where=where(lesson))
        module = lesson.module
        lesson.delete()
        renumber(module)
        return Response({'ok': True})

    if request.method == 'PATCH':
        d = request.data
        changes = {}
        for f in ('title_kz', 'title_ru'):
            if f in d and d[f] != getattr(lesson, f):
                changes[f] = [getattr(lesson, f), d[f]]
                setattr(lesson, f, d[f])
        if 'status' in d and d['status'] != lesson.status:
            if d['status'] == PUBLISHED and not readiness(lesson)['ok']:
                raise ValidationError({'status': 'Урок не готов к публикации — см. «Готовность к публикации»'})
            changes['status'] = [lesson.status, d['status']]
            set_status(lesson, d['status'])
        old_module = lesson.module
        if 'module_id' in d and int(d['module_id']) != old_module.id:
            new_module = get_object_or_404(Module, pk=d['module_id'])
            lesson.module, lesson.code = new_module, free_code(new_module)
            lesson.sort_order = new_module.lessons.count()
            changes['module'] = [old_module.number, new_module.number]
        lesson.updated_by = request.user
        lesson.save()
        if lesson.module != old_module:
            renumber(old_module)
        if 'position' in d:
            renumber(lesson.module, lesson, int(d['position']))
        if changes:
            audit(request, AuditLog.Action.UPDATE, lesson, where=where(lesson), fields=list(changes))
        lesson.refresh_from_db()
    return Response(lesson_detail(lesson))


@panel(['POST'])
@transaction.atomic
def lesson_publish(request, pk):
    lesson = get_object_or_404(Lesson.objects.select_related('module__level'), pk=pk)
    ready = readiness(lesson)
    if not ready['ok']:
        raise ValidationError({'detail': 'Урок не готов к публикации', 'readiness': ready})
    set_status(lesson, PUBLISHED)
    lesson.updated_by = request.user
    lesson.save()
    # Содержимое урока тоже становится видно ученикам
    lesson.words.update(status=PUBLISHED)
    lesson.texts.update(status=PUBLISHED)
    lesson.grammar_rules.update(status=PUBLISHED)
    lesson.quizzes.update(status=PUBLISHED)
    audit(request, AuditLog.Action.PUBLISH, lesson, where=where(lesson))
    return Response(lesson_detail(lesson))


def ensure_block(lesson, block):
    if block not in UI_BLOCKS:
        raise ValidationError({'type': 'Неизвестный блок'})
    order = len(lesson_blocks(lesson))
    for t in UI_BLOCKS[block]:
        LessonBlock.objects.get_or_create(lesson=lesson, block_type=t, defaults={'sort_order': order})


@panel(['POST'])
@transaction.atomic
def blocks_add(request, pk):
    lesson = get_object_or_404(Lesson.objects.select_related('module__level'), pk=pk)
    block = request.data.get('type')
    if block in lesson_blocks(lesson):
        raise ValidationError({'type': 'Такой блок уже есть в уроке'})
    ensure_block(lesson, block)
    audit(request, AuditLog.Action.UPDATE, lesson, where=where(lesson), added_block=block)
    return Response(lesson_detail(lesson), status=status.HTTP_201_CREATED)


@panel(['DELETE'])
@transaction.atomic
def blocks_delete(request, pk, block):
    """Удаляет блок вместе с его содержимым (слова, правило, текст или тест урока)."""
    lesson = get_object_or_404(Lesson.objects.select_related('module__level'), pk=pk)
    if block not in UI_BLOCKS:
        raise ValidationError({'type': 'Неизвестный блок'})
    lesson.blocks.filter(block_type__in=UI_BLOCKS[block]).delete()
    {'cards': lesson.words, 'grammar': lesson.grammar_rules, 'text': lesson.texts, 'quiz': lesson.quizzes}[block].all().delete()
    audit(request, AuditLog.Action.DELETE, lesson, where=where(lesson), removed_block=block)
    return Response(lesson_detail(lesson))


@panel(['POST'])
@transaction.atomic
def blocks_reorder(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)
    order = [b for b in request.data.get('types', []) if b in UI_BLOCKS]
    for i, block in enumerate(order):
        lesson.blocks.filter(block_type__in=UI_BLOCKS[block]).update(sort_order=i)
    return Response(lesson_detail(Lesson.objects.select_related('module__level').get(pk=pk)))


# =====================================================================
#  Карточки слов
# =====================================================================

WORD_FIELDS = ('kz', 'ru', 'transcription', 'part_of_speech', 'example_kz', 'example_ru')


def apply_word(word, d):
    for f in WORD_FIELDS:
        if f in d:
            setattr(word, f, (d[f] or '').strip())
    if 'status' in d:
        set_status(word, d['status'])
    if 'image_id' in d:
        word.image = get_object_or_404(MediaFile, pk=d['image_id'], kind=MediaFile.Kind.IMAGE) if d['image_id'] else None
    if not word.kz or not word.ru:
        raise ValidationError({'kz' if not word.kz else 'ru': 'Обязательное поле'})


@panel(['GET', 'POST'])
@transaction.atomic
def words(request, pk):
    lesson = get_object_or_404(Lesson.objects.select_related('module__level'), pk=pk)
    if request.method == 'POST':
        word = Word(lesson=lesson, sort_order=(lesson.words.aggregate(m=Max('sort_order'))['m'] or -1) + 1,
                    status=PUBLISHED)
        apply_word(word, request.data)
        word.save()
        ensure_block(lesson, 'cards') if 'cards' not in lesson_blocks(lesson) else None
        audit(request, AuditLog.Action.CREATE, word, where=where(lesson))
        return Response(word_data(word), status=status.HTTP_201_CREATED)
    return Response({
        'lesson': lesson_head(lesson),
        'words': [word_data(w) for w in lesson.words.select_related('image').order_by('sort_order', 'id')],
    })


@panel(['PATCH', 'DELETE'])
def word(request, pk):
    word = get_object_or_404(Word.objects.select_related('lesson__module__level'), pk=pk)
    if request.method == 'DELETE':
        audit(request, AuditLog.Action.DELETE, word, where=where(word.lesson))
        word.delete()
        return Response({'ok': True})
    apply_word(word, request.data)
    word.save()
    audit(request, AuditLog.Action.UPDATE, word, where=where(word.lesson))
    return Response(word_data(word))


@panel(['POST'])
@transaction.atomic
def words_bulk(request, pk):
    lesson = get_object_or_404(Lesson.objects.select_related('module__level'), pk=pk)
    ids = [int(i) for i in request.data.get('ids', [])]
    action = request.data.get('action')
    qs = lesson.words.filter(pk__in=ids)
    if action == 'publish':
        n = qs.update(status=PUBLISHED)
    elif action == 'delete':
        n = qs.count()
        qs.delete()
    else:
        raise ValidationError({'action': 'Нужно publish или delete'})
    audit(request, AuditLog.Action.PUBLISH if action == 'publish' else AuditLog.Action.DELETE, lesson,
          where=where(lesson), words=n)
    return Response({'ok': True, 'count': n})


@panel(['POST'])
@transaction.atomic
def words_import(request, pk):
    """CSV: kz;ru;part_of_speech;example_kz;example_ru — одна строка = одна карточка."""
    lesson = get_object_or_404(Lesson.objects.select_related('module__level'), pk=pk)
    raw = request.data.get('csv', '')
    order = (lesson.words.aggregate(m=Max('sort_order'))['m'] or -1) + 1
    created = []
    for row in csv.reader(io.StringIO(raw), delimiter=';'):
        row = [c.strip() for c in row] + [''] * 5
        kz, ru, pos, ex_kz, ex_ru = row[:5]
        if not kz or not ru or kz.lower() == 'kz':
            continue
        created.append(Word(lesson=lesson, kz=kz, ru=ru, part_of_speech=pos, example_kz=ex_kz, example_ru=ex_ru,
                            sort_order=order + len(created), status=PUBLISHED))
    if not created:
        raise ValidationError({'csv': 'Не нашёл ни одной строки вида «слово;перевод»'})
    Word.objects.bulk_create(created)
    if 'cards' not in lesson_blocks(lesson):
        ensure_block(lesson, 'cards')
    audit(request, AuditLog.Action.CREATE, lesson, where=where(lesson), imported_words=len(created))
    return Response({'ok': True, 'count': len(created)}, status=status.HTTP_201_CREATED)


@panel(['POST'], parsers=[MultiPartParser, FormParser])
def media_upload(request):
    f = request.FILES.get('file')
    if not f:
        raise ValidationError({'file': 'Нужен файл'})
    kind = MediaFile.Kind.IMAGE if (f.content_type or '').startswith('image/') else None
    if kind is None:
        raise ValidationError({'file': 'Пока можно загружать только картинки'})
    media = MediaFile.objects.create(kind=kind, file=f, mime_type=f.content_type or '', uploaded_by=request.user)
    audit(request, AuditLog.Action.CREATE, media)
    return Response({'id': media.id, 'url': media.file.url}, status=status.HTTP_201_CREATED)


# =====================================================================
#  Грамматика, текст, тест
# =====================================================================

def grammar_data(rule):
    if rule is None:
        return {'title_kz': '', 'title_ru': '', 'explanation': '', 'table': [], 'examples': []}
    return {
        'title_kz': rule.title_kz,
        'title_ru': rule.title_ru,
        'explanation': rule.explanation,
        'table': [{'form': r.form_label, 'pattern': r.pattern, 'example': r.example} for r in rule.table_rows.all()],
        'examples': [{'kz': e.text_kz, 'ru': e.text_ru} for e in rule.examples.all()],
    }




@panel(['GET', 'PUT'])
@transaction.atomic
def grammar(request, pk):
    lesson = get_object_or_404(Lesson.objects.select_related('module__level'), pk=pk)
    rule = lesson.grammar_rules.order_by('sort_order').first()
    if request.method == 'PUT':
        d = request.data
        require(d, 'title_kz')
        if rule is None:
            rule = GrammarRule(lesson=lesson, status=PUBLISHED)
        rule.title_kz, rule.title_ru, rule.explanation = d['title_kz'], d.get('title_ru', ''), d.get('explanation', '')
        rule.save()
        rule.table_rows.all().delete()
        GrammarTableRow.objects.bulk_create(
            GrammarTableRow(rule=rule, form_label=r.get('form', ''), pattern=r.get('pattern', ''),
                            example=r.get('example', ''), sort_order=i)
            for i, r in enumerate(d.get('table', [])) if any(str(v).strip() for v in r.values())
        )
        rule.examples.all().delete()
        GrammarExample.objects.bulk_create(
            GrammarExample(rule=rule, text_kz=e['kz'], text_ru=e.get('ru', ''), sort_order=i)
            for i, e in enumerate(d.get('examples', [])) if e.get('kz', '').strip()
        )
        if 'grammar' not in lesson_blocks(lesson):
            ensure_block(lesson, 'grammar')
        audit(request, AuditLog.Action.UPDATE, rule, where=where(lesson))
    return Response({'lesson': lesson_head(lesson), 'grammar': grammar_data(rule)})


@panel(['GET', 'PUT'])
@transaction.atomic
def text_quiz(request, pk):
    """Текст для чтения и тест к нему — один экран в макете (6 · Текст и тест)."""
    lesson = get_object_or_404(Lesson.objects.select_related('module__level'), pk=pk)
    if request.method == 'PUT':
        d = request.data
        if 'text' in d:
            t = d['text'] or {}
            paragraphs = [p.strip() for p in t.get('paragraphs', []) if p.strip()]
            text = lesson.texts.first() or Text(lesson=lesson, status=PUBLISHED)
            text.title, text.body = (t.get('title') or '').strip(), '\n\n'.join(paragraphs)
            if not text.title:
                raise ValidationError({'text': 'Нужен заголовок текста'})
            text.save()
            if 'text' not in lesson_blocks(lesson):
                ensure_block(lesson, 'text')
            audit(request, AuditLog.Action.UPDATE, text, where=where(lesson))
        if 'questions' in d:
            questions = d['questions'] or []
            for i, q in enumerate(questions, 1):
                opts = q.get('options', [])
                if not str(q.get('prompt', '')).strip() or len(opts) < 2 or any(not str(o).strip() for o in opts):
                    raise ValidationError({'questions': f'Вопрос {i}: нужен текст и минимум 2 заполненных варианта'})
                if q.get('correct') is None or not 0 <= int(q['correct']) < len(q.get('options', [])):
                    raise ValidationError({'questions': f'Вопрос {i}: отметьте правильный ответ'})
            text = lesson.texts.first()
            quiz = lesson.quizzes.first() or Quiz.objects.create(
                lesson=lesson, title=f'Сұрақтар: {text.title if text else lesson.title_kz}'[:200], status=PUBLISHED)
            saved = sync_ordered(QuizQuestion, 'quiz', quiz, [
                {'question_type': QuizQuestion.Type.SINGLE, 'prompt': q['prompt'].strip()} for q in questions
            ])
            for q, src in zip(saved, questions):
                sync_ordered(QuizOption, 'question', q, [
                    {'text': str(o).strip(), 'is_correct': j == int(src['correct'])}
                    for j, o in enumerate(src['options'])
                ])
            if 'quiz' not in lesson_blocks(lesson):
                ensure_block(lesson, 'quiz')
            audit(request, AuditLog.Action.UPDATE, quiz, where=where(lesson), questions=len(questions))

    text = lesson.texts.first()
    quiz = lesson.quizzes.prefetch_related('questions__options').first()
    return Response({
        'lesson': lesson_head(lesson),
        'text': {'title': text.title, 'paragraphs': text.paragraphs} if text else {'title': '', 'paragraphs': []},
        'questions': [
            {
                'id': q.id,
                'prompt': q.prompt,
                'options': [o.text for o in q.options.all()],
                'correct': next((j for j, o in enumerate(q.options.all()) if o.is_correct), None),
            }
            for q in (quiz.questions.all() if quiz else [])
        ],
    })
