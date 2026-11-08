"""Загружает контент из data/content.json в таблицы levels, modules, lessons, lesson_blocks, words,
texts, grammar_rules, grammar_table_rows, grammar_examples, quizzes, quiz_questions, quiz_options.

Повторный запуск обновляет данные. Слова, вопросы и варианты ответа обновляются по порядку
(sort_order), а не пересоздаются — так прогресс учеников не теряется.

В content.json у модуля 4 урока заданы только названиями, а слова, грамматика, текст и вопросы
общие на модуль. Поэтому весь учебный материал модуля кладётся в его первый урок.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from learning.models import (
    GrammarExample,
    GrammarRule,
    GrammarTableRow,
    Lesson,
    LessonBlock,
    Level,
    Module,
    Quiz,
    QuizOption,
    QuizQuestion,
    Status,
    Text,
    Word,
)

DEFAULT_FILE = Path(__file__).resolve().parents[2] / 'data' / 'content.json'

CONTENT_BLOCKS = [
    LessonBlock.Type.WORDS,
    LessonBlock.Type.CARDS,
    LessonBlock.Type.GRAMMAR,
    LessonBlock.Type.TEXT,
    LessonBlock.Type.QUIZ,
]

PUBLISHED = Status.PUBLISHED


def sync_ordered(model, parent_field, parent, items):
    """update_or_create по (родитель, sort_order); лишние записи удаляются. Возвращает объекты по порядку."""
    objs = []
    for i, defaults in enumerate(items):
        obj, _ = model.objects.update_or_create(**{parent_field: parent, 'sort_order': i}, defaults=defaults)
        objs.append(obj)
    model.objects.filter(**{parent_field: parent, 'sort_order__gte': len(items)}).delete()
    return objs


class Command(BaseCommand):
    help = 'Загружает уровни, модули, уроки, слова, грамматику, тексты и тесты из JSON.'

    def add_arguments(self, parser):
        parser.add_argument('--file', default=str(DEFAULT_FILE))

    @transaction.atomic
    def handle(self, *args, **opts):
        data = json.loads(Path(opts['file']).read_text(encoding='utf-8'))
        now = timezone.now()

        levels = {}
        for lv in data['levels']:
            levels[lv['code']], _ = Level.objects.update_or_create(
                code=lv['code'],
                defaults={
                    'title_kz': lv['title'],
                    'title_ru': lv['title_ru'],
                    'description': lv.get('description', ''),
                    'sort_order': lv.get('order', 0),
                    'is_published': lv.get('available', False),
                },
            )

        for m in data['modules']:
            module, _ = Module.objects.update_or_create(
                level=levels[m['level']],
                number=m['number'],
                defaults={
                    'title_kz': m['title'],
                    'title_ru': m['title_ru'],
                    'emoji': m['emoji'],
                    'color': m['color'],
                    'sort_order': m['number'],
                    'status': PUBLISHED,
                },
            )
            if module.published_at is None:
                Module.objects.filter(pk=module.pk).update(published_at=now)

            lessons = []
            for i, title in enumerate(m['lessons']):
                lesson, _ = Lesson.objects.update_or_create(
                    module=module,
                    code=f"{m['number']}.{i + 1}",
                    defaults={'title_kz': title, 'sort_order': i, 'status': PUBLISHED, 'published_at': now},
                )
                lessons.append(lesson)
            module.lessons.exclude(pk__in=[l.pk for l in lessons]).delete()
            main = lessons[0]

            for j, block in enumerate(CONTENT_BLOCKS):
                LessonBlock.objects.update_or_create(lesson=main, block_type=block, defaults={'sort_order': j})

            # Слова
            sync_ordered(Word, 'lesson', main, [
                {'kz': w['kz'], 'ru': w['ru'], 'status': PUBLISHED} for w in m['words']
            ])

            # Текст: абзацы → body через пустую строку
            text = m['text']
            Text.objects.update_or_create(
                lesson=main,
                defaults={'title': text['title'], 'body': '\n\n'.join(text['paragraphs']), 'status': PUBLISHED},
            )

            # Грамматика (на правила прогресс не ссылается — пересоздаём)
            g = m['grammar']
            main.grammar_rules.all().delete()
            rule = GrammarRule.objects.create(
                lesson=main, title_kz=g['title'], title_ru=g['titleRu'],
                explanation=g.get('explanation', ''), status=PUBLISHED,
            )
            GrammarTableRow.objects.bulk_create(
                GrammarTableRow(rule=rule, form_label=r[0], pattern=r[1], example=r[2], sort_order=i)
                for i, r in enumerate(g.get('table', []))
            )
            GrammarExample.objects.bulk_create(
                GrammarExample(rule=rule, text_kz=e[0], text_ru=e[1] if len(e) > 1 else '', sort_order=i)
                for i, e in enumerate(g.get('examples', []))
            )

            # Тест по тексту
            quiz, _ = Quiz.objects.update_or_create(
                lesson=main, defaults={'title': f"Сұрақтар: {text['title']}"[:200], 'status': PUBLISHED},
            )
            questions = sync_ordered(QuizQuestion, 'quiz', quiz, [
                {'question_type': QuizQuestion.Type.SINGLE, 'prompt': q['text']} for q in m['questions']
            ])
            for q, src in zip(questions, m['questions']):
                sync_ordered(QuizOption, 'question', q, [
                    {'text': opt, 'is_correct': i == src['answer']} for i, opt in enumerate(src['options'])
                ])

        if opts['verbosity'] > 0:
            self.stdout.write(self.style.SUCCESS(
                f'Загружено: уровней {Level.objects.count()}, модулей {Module.objects.count()}, '
                f'уроков {Lesson.objects.count()}, слов {Word.objects.count()}, '
                f'вопросов {QuizQuestion.objects.count()}'
            ))
