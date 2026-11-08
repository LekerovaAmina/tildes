"""Сериализация в формат, который ждёт фронтенд (frontend/src/store/content.jsx).

Фронтенд работает с «модулями» (темами): слова, грамматика, текст, вопросы. В базе этот материал
лежит в уроках модуля — здесь он собирается обратно в одну тему.
"""

from django.db.models import Prefetch
from rest_framework import serializers

from .models import (
    GrammarRule,
    Lesson,
    Quiz,
    QuizQuestion,
    Status,
    Text,
    Word,
)

PUBLISHED = Status.PUBLISHED


# ---------- Запросы с подгрузкой связей ----------

def modules_with_content(qs):
    """Модули со всем опубликованным содержимым уроков — без запросов в цикле."""
    lessons = Lesson.objects.filter(status=PUBLISHED).order_by('sort_order').prefetch_related(
        Prefetch('words', Word.objects.filter(status=PUBLISHED).order_by('sort_order')),
        Prefetch('texts', Text.objects.filter(status=PUBLISHED).order_by('id')),
        Prefetch(
            'grammar_rules',
            GrammarRule.objects.filter(status=PUBLISHED).order_by('sort_order').prefetch_related('table_rows', 'examples'),
        ),
        Prefetch(
            'quizzes',
            Quiz.objects.filter(status=PUBLISHED).order_by('id').prefetch_related(
                Prefetch('questions', QuizQuestion.objects.order_by('sort_order').prefetch_related('options')),
            ),
        ),
    )
    return qs.filter(status=PUBLISHED).select_related('level').prefetch_related(Prefetch('lessons', lessons))


def module_quiz(module):
    """Тест темы — первый опубликованный тест в её уроках (по порядку уроков)."""
    for lesson in module.lessons.all():
        quizzes = list(lesson.quizzes.all())
        if quizzes:
            return quizzes[0]
    return None


# ---------- Представления ----------

def level_data(level):
    return {
        'code': level.code,
        'title': level.title_kz,
        'title_ru': level.title_ru,
        'description': level.description,
        'available': level.is_published,
    }


def word_data(word, module_id):
    return {'id': word.id, 'kz': word.kz, 'ru': word.ru, 'module_id': module_id}


def grammar_data(rule):
    if rule is None:
        return {}
    return {
        'title': rule.title_kz,
        'titleRu': rule.title_ru,
        'explanation': rule.explanation,
        'table': [[r.form_label, r.pattern, r.example] for r in rule.table_rows.all()],
        'examples': [[e.text_kz, e.text_ru] for e in rule.examples.all()],
    }


def module_short(module):
    """Для списка модулей. Ожидает modules_with_content()."""
    quiz = module_quiz(module)
    lessons = list(module.lessons.all())
    return {
        'id': module.id,
        'number': module.number,
        'title': module.title_kz,
        'title_ru': module.title_ru,
        'emoji': module.emoji,
        'color': module.color,
        'lessons': [l.title_kz for l in lessons],
        'word_count': sum(len(l.words.all()) for l in lessons),
        'question_count': len(quiz.questions.all()) if quiz else 0,
    }


def module_detail(module):
    """Полная тема. Правильные ответы не отдаём — проверка на сервере."""
    lessons = list(module.lessons.all())
    words = [word_data(w, module.id) for l in lessons for w in l.words.all()]
    rule = next((r for l in lessons for r in l.grammar_rules.all()), None)
    text = next((t for l in lessons for t in l.texts.all()), None)
    quiz = module_quiz(module)
    return {
        'id': module.id,
        'number': module.number,
        'title': module.title_kz,
        'title_ru': module.title_ru,
        'emoji': module.emoji,
        'color': module.color,
        'lessons': [l.title_kz for l in lessons],
        'words': words,
        'grammar': grammar_data(rule),
        'text': {'title': text.title, 'paragraphs': text.paragraphs} if text else {'title': '', 'paragraphs': []},
        'questions': [
            {'id': q.id, 'text': q.prompt, 'options': [o.text for o in q.options.all()]}
            for q in (quiz.questions.all() if quiz else [])
        ],
    }


# ---------- Входные данные ----------

class CardAnswerSerializer(serializers.Serializer):
    word_id = serializers.IntegerField()
    result = serializers.ChoiceField(choices=['learned', 'again'])


class CardCompleteSerializer(serializers.Serializer):
    module_id = serializers.IntegerField(required=False, allow_null=True)  # null — режим «Повторение»


class QuizSubmitSerializer(serializers.Serializer):
    answers = serializers.ListField(child=serializers.IntegerField(allow_null=True))


class ReadSerializer(serializers.Serializer):
    module_id = serializers.IntegerField()
    section = serializers.ChoiceField(choices=['words', 'grammar', 'text'])


class ProfileUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    level = serializers.CharField(max_length=4, required=False)

