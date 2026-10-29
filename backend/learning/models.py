from django.db import models


# ---------- Контент ----------

class Level(models.Model):
    code = models.CharField('Код', max_length=4, primary_key=True)  # A1 … C1
    title = models.CharField('Название (каз.)', max_length=100)
    title_ru = models.CharField('Название (рус.)', max_length=100)
    description = models.CharField('Описание', max_length=255, blank=True)
    available = models.BooleanField('Доступен', default=False)
    order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'Уровень'
        verbose_name_plural = 'Уровни'

    def __str__(self):
        return self.code


class Module(models.Model):
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='modules', verbose_name='Уровень')
    number = models.PositiveSmallIntegerField('Номер')
    title = models.CharField('Тема (каз.)', max_length=200)
    title_ru = models.CharField('Тема (рус.)', max_length=200)
    emoji = models.CharField(max_length=8, blank=True)
    color = models.CharField('Цвет', max_length=9, default='#8B5CF6')
    lessons = models.JSONField('Уроки', default=list)
    # {title, titleRu, explanation, table: [[форма, правило, пример]], examples: [[каз, рус]]}
    grammar = models.JSONField('Грамматика', default=dict, blank=True)
    text_title = models.CharField('Заголовок текста', max_length=200, blank=True)
    text_paragraphs = models.JSONField('Абзацы текста', default=list, blank=True)

    class Meta:
        ordering = ['level', 'number']
        unique_together = [('level', 'number')]
        verbose_name = 'Модуль (тема)'
        verbose_name_plural = 'Модули (темы)'

    def __str__(self):
        return f'{self.level_id} · {self.number}. {self.title}'


class Word(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='words', verbose_name='Модуль')
    order = models.PositiveSmallIntegerField(default=0)
    kz = models.CharField('Слово (каз.)', max_length=120)
    ru = models.CharField('Перевод', max_length=200)

    class Meta:
        ordering = ['module', 'order']
        verbose_name = 'Слово'
        verbose_name_plural = 'Слова'

    def __str__(self):
        return f'{self.kz} — {self.ru}'


class Question(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='questions', verbose_name='Модуль')
    order = models.PositiveSmallIntegerField(default=0)
    text = models.CharField('Вопрос', max_length=300)
    options = models.JSONField('Варианты', default=list)
    answer = models.PositiveSmallIntegerField('Индекс правильного ответа')

    class Meta:
        ordering = ['module', 'order']
        verbose_name = 'Вопрос к тексту'
        verbose_name_plural = 'Вопросы к тексту'

    def __str__(self):
        return self.text


# ---------- Прогресс ----------

class Learner(models.Model):
    """Пользователь MVP без регистрации: определяется заголовком X-Device-Id.
    Когда появится авторизация — добавить OneToOneField на User."""

    device_id = models.CharField(max_length=64, unique=True)
    name = models.CharField('Имя', max_length=60, blank=True)
    level = models.ForeignKey(Level, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Уровень')
    points = models.PositiveIntegerField('Баллы', default=0)
    active_days = models.JSONField('Дни активности', default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-points']
        verbose_name = 'Ученик'
        verbose_name_plural = 'Ученики'

    def __str__(self):
        return self.name or self.device_id[:8]


class WordStat(models.Model):
    learner = models.ForeignKey(Learner, on_delete=models.CASCADE, related_name='word_stats')
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    learned = models.PositiveIntegerField(default=0)  # «Я выучил»
    again = models.PositiveIntegerField(default=0)  # «Учить ещё раз»
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('learner', 'word')]


class CompletedTopic(models.Model):
    learner = models.ForeignKey(Learner, on_delete=models.CASCADE, related_name='completed_topics')
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('learner', 'module')]


class QuizResult(models.Model):
    learner = models.ForeignKey(Learner, on_delete=models.CASCADE, related_name='quiz_results')
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    best = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = [('learner', 'module')]


class TopicRead(models.Model):
    learner = models.ForeignKey(Learner, on_delete=models.CASCADE, related_name='topic_reads')
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    words = models.BooleanField(default=False)
    grammar = models.BooleanField(default=False)
    text = models.BooleanField(default=False)

    class Meta:
        unique_together = [('learner', 'module')]
