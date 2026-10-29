import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from learning.models import Level, Module, Question, Word

DEFAULT_FILE = Path(__file__).resolve().parents[2] / 'data' / 'content.json'


class Command(BaseCommand):
    help = 'Загружает уровни и модули (слова, грамматику, тексты, вопросы) из JSON. Повторный запуск обновляет данные.'

    def add_arguments(self, parser):
        parser.add_argument('--file', default=str(DEFAULT_FILE))

    @transaction.atomic
    def handle(self, *args, **opts):
        data = json.loads(Path(opts['file']).read_text(encoding='utf-8'))

        for lv in data['levels']:
            Level.objects.update_or_create(code=lv.pop('code'), defaults=lv)

        for m in data['modules']:
            module, _ = Module.objects.update_or_create(
                level_id=m['level'],
                number=m['number'],
                defaults={
                    'title': m['title'],
                    'title_ru': m['title_ru'],
                    'emoji': m['emoji'],
                    'color': m['color'],
                    'lessons': m['lessons'],
                    'grammar': m['grammar'],
                    'text_title': m['text']['title'],
                    'text_paragraphs': m['text']['paragraphs'],
                },
            )
            # Слова обновляем по порядку, чтобы не терять статистику учеников
            for i, w in enumerate(m['words']):
                Word.objects.update_or_create(module=module, order=i, defaults=w)
            module.words.filter(order__gte=len(m['words'])).delete()

            module.questions.all().delete()
            Question.objects.bulk_create(Question(module=module, order=i, **q) for i, q in enumerate(m['questions']))

        self.stdout.write(self.style.SUCCESS(
            f"Загружено: уровней {Level.objects.count()}, модулей {Module.objects.count()}, слов {Word.objects.count()}"
        ))
