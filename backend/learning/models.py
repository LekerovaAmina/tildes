"""Схема базы данных Tildes (23 таблицы).

Группы:
  • Пользователи и контент — users, levels, modules, lessons, lesson_blocks, words, texts,
    grammar_rules, grammar_table_rows, grammar_examples, quizzes, quiz_questions, quiz_options, media_files
  • Прогресс ученика — point_transactions, user_activity_days, user_word_progress, user_lesson_progress,
    card_sessions, card_answers, quiz_attempts, quiz_attempt_answers
  • Админка — audit_log

Зарезервированы на будущее (пока не создаются): listening_tasks, speaking_tasks, writing_tasks.
Имена таблиц заданы явно (db_table), чтобы совпадать с макетом.
"""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone


class Status(models.TextChoices):
    DRAFT = 'draft', 'Черновик'
    REVIEW = 'review', 'На проверке'
    PUBLISHED = 'published', 'Опубликовано'
    ARCHIVED = 'archived', 'В архиве'


def status_field():
    return models.CharField('Статус', max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)


class Timestamped(models.Model):
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Изменено', auto_now=True)

    class Meta:
        abstract = True


# =====================================================================
#  Пользователи
# =====================================================================

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('Нужен email')
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)  # password=None → непригодный для входа пароль
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('role', User.Role.ADMIN)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser):
    """Таблица users. Поля password и last_login приходят из AbstractBaseUser."""

    class Role(models.TextChoices):
        STUDENT = 'student', 'Ученик'
        EDITOR = 'editor', 'Редактор контента'
        ADMIN = 'admin', 'Администратор'

    # Пока нет регистрации, устройство (X-Device-Id) получает такой технический email
    DEVICE_EMAIL_DOMAIN = 'device.tildes.local'

    email = models.EmailField('Email', max_length=254, unique=True)
    display_name = models.CharField('Имя', max_length=80, blank=True)
    role = models.CharField('Роль', max_length=10, choices=Role.choices, default=Role.STUDENT)
    current_level = models.ForeignKey(
        'Level', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Текущий уровень',
    )
    points = models.PositiveIntegerField('Баллы', default=0, db_index=True)
    is_active = models.BooleanField('Активен', default=True)
    is_superuser = models.BooleanField('Суперпользователь', default=False)
    date_joined = models.DateTimeField('Дата регистрации', default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        if self.is_device:
            return self.display_name or f'Устройство {self.email[:8]}'
        return self.display_name or self.email

    @property
    def is_device(self):
        return self.email.endswith('@' + self.DEVICE_EMAIL_DOMAIN)

    # --- доступ в админку ---
    @property
    def is_staff(self):
        return self.is_active and (self.is_superuser or self.role in (self.Role.EDITOR, self.Role.ADMIN))

    CONTENT_MODELS = {
        'level', 'module', 'lesson', 'lessonblock', 'word', 'text', 'grammarrule', 'grammartablerow',
        'grammarexample', 'quiz', 'quizquestion', 'quizoption', 'mediafile',
    }

    def has_perm(self, perm, obj=None):
        if not self.is_active:
            return False
        if self.is_superuser or self.role == self.Role.ADMIN:
            return True
        if self.role == self.Role.EDITOR:
            app, _, codename = perm.partition('.')
            model = codename.split('_', 1)[-1]
            return app == 'learning' and model in self.CONTENT_MODELS
        return False

    def has_perms(self, perms, obj=None):
        return all(self.has_perm(p, obj) for p in perms)

    def has_module_perms(self, app_label):
        return self.is_staff


# =====================================================================
#  Контент
# =====================================================================

class Level(Timestamped):
    code = models.CharField('Код', max_length=4, unique=True)  # A1 … C1
    title_kz = models.CharField('Название (каз.)', max_length=120)
    title_ru = models.CharField('Название (рус.)', max_length=120)
    description = models.TextField('Описание', blank=True)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_published = models.BooleanField('Опубликован', default=False)

    class Meta:
        db_table = 'levels'
        ordering = ['sort_order']
        verbose_name = 'Уровень'
        verbose_name_plural = 'Уровни'

    def __str__(self):
        return self.code


class MediaFile(models.Model):
    class Kind(models.TextChoices):
        IMAGE = 'image', 'Изображение'
        AUDIO = 'audio', 'Аудио'
        VIDEO = 'video', 'Видео'

    kind = models.CharField('Тип', max_length=10, choices=Kind.choices)
    file = models.FileField('Файл', max_length=255, upload_to='media/%Y/%m/')
    mime_type = models.CharField('MIME-тип', max_length=100, blank=True)
    size_bytes = models.PositiveIntegerField('Размер, байт', default=0)
    duration_sec = models.DecimalField('Длительность, с', max_digits=8, decimal_places=2, null=True, blank=True)
    uploaded_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Загрузил',
        db_column='uploaded_by',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        db_table = 'media_files'
        ordering = ['-created_at']
        verbose_name = 'Медиафайл'
        verbose_name_plural = 'Медиафайлы'

    def __str__(self):
        return self.file.name

    def save(self, *args, **kwargs):
        if self.file and not self.size_bytes:
            try:
                self.size_bytes = self.file.size
            except (OSError, ValueError):
                pass
        super().save(*args, **kwargs)


class Module(Timestamped):
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='modules', verbose_name='Уровень')
    number = models.PositiveSmallIntegerField('Номер')
    title_kz = models.CharField('Тема (каз.)', max_length=200)
    title_ru = models.CharField('Тема (рус.)', max_length=200)
    emoji = models.CharField(max_length=8, blank=True)
    color = models.CharField('Цвет', max_length=7, default='#8B5CF6')  # char(7): #RRGGBB
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)
    status = status_field()
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Автор',
        db_column='created_by',
    )
    published_at = models.DateTimeField('Опубликовано', null=True, blank=True)

    class Meta:
        db_table = 'modules'
        ordering = ['level__sort_order', 'sort_order', 'number']
        constraints = [models.UniqueConstraint(fields=['level', 'number'], name='modules_level_number_uniq')]
        verbose_name = 'Модуль (тема)'
        verbose_name_plural = 'Модули (темы)'

    def __str__(self):
        return f'{self.level.code} · {self.number}. {self.title_kz}'


class Lesson(Timestamped):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons', verbose_name='Модуль')
    code = models.CharField('Код', max_length=4)  # «1.1», «10.4»
    title_kz = models.CharField('Название (каз.)', max_length=200)
    title_ru = models.CharField('Название (рус.)', max_length=200, blank=True)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)
    status = status_field()
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Автор',
        db_column='created_by',
    )
    updated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Изменил',
        db_column='updated_by',
    )
    published_at = models.DateTimeField('Опубликовано', null=True, blank=True)

    class Meta:
        db_table = 'lessons'
        ordering = ['module', 'sort_order']
        constraints = [models.UniqueConstraint(fields=['module', 'code'], name='lessons_module_code_uniq')]
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'

    def __str__(self):
        return f'{self.code}. {self.title_kz}'


class LessonBlock(models.Model):
    """Какие разделы есть в уроке и в каком порядке они идут."""

    class Type(models.TextChoices):
        WORDS = 'words', 'Сөздер (слова)'
        CARDS = 'cards', 'Карточки'
        GRAMMAR = 'grammar', 'Грамматика'
        TEXT = 'text', 'Мәтін (текст)'
        QUIZ = 'quiz', 'Сұрақтар (тест)'

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='blocks', verbose_name='Урок')
    block_type = models.CharField('Тип блока', max_length=12, choices=Type.choices)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_enabled = models.BooleanField('Включён', default=True)

    class Meta:
        db_table = 'lesson_blocks'
        ordering = ['lesson', 'sort_order']
        constraints = [models.UniqueConstraint(fields=['lesson', 'block_type'], name='lesson_blocks_lesson_type_uniq')]
        verbose_name = 'Блок урока'
        verbose_name_plural = 'Блоки урока'

    def __str__(self):
        return self.get_block_type_display()


class Word(Timestamped):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='words', verbose_name='Урок')
    kz = models.CharField('Слово (каз.)', max_length=200)
    ru = models.CharField('Перевод', max_length=300)
    transcription = models.CharField('Транскрипция', max_length=200, blank=True)
    part_of_speech = models.CharField('Часть речи', max_length=30, blank=True)
    example_kz = models.TextField('Пример (каз.)', blank=True)
    example_ru = models.TextField('Пример (рус.)', blank=True)
    image = models.ForeignKey(
        MediaFile, null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Картинка',
        limit_choices_to={'kind': MediaFile.Kind.IMAGE},
    )
    audio = models.ForeignKey(
        MediaFile, null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Аудио',
        limit_choices_to={'kind': MediaFile.Kind.AUDIO},
    )
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)
    status = status_field()

    class Meta:
        db_table = 'words'
        ordering = ['lesson', 'sort_order']
        verbose_name = 'Слово'
        verbose_name_plural = 'Слова'

    def __str__(self):
        return f'{self.kz} — {self.ru}'


class Text(Timestamped):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='texts', verbose_name='Урок')
    title = models.CharField('Заголовок', max_length=200)
    body = models.TextField('Текст', help_text='Абзацы разделяются пустой строкой')
    translation_ru = models.TextField('Перевод', blank=True)
    audio = models.ForeignKey(
        MediaFile, null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Аудио',
        limit_choices_to={'kind': MediaFile.Kind.AUDIO},
    )
    status = status_field()

    class Meta:
        db_table = 'texts'
        ordering = ['lesson', 'id']
        verbose_name = 'Текст'
        verbose_name_plural = 'Тексты'

    def __str__(self):
        return self.title

    @property
    def paragraphs(self):
        return [p.strip() for p in self.body.split('\n\n') if p.strip()]


class GrammarRule(Timestamped):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='grammar_rules', verbose_name='Урок')
    title_kz = models.CharField('Название (каз.)', max_length=200)
    title_ru = models.CharField('Название (рус.)', max_length=200)
    explanation = models.TextField('Объяснение', blank=True)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)
    status = status_field()

    class Meta:
        db_table = 'grammar_rules'
        ordering = ['lesson', 'sort_order']
        verbose_name = 'Правило грамматики'
        verbose_name_plural = 'Правила грамматики'

    def __str__(self):
        return self.title_kz


class GrammarTableRow(models.Model):
    rule = models.ForeignKey(GrammarRule, on_delete=models.CASCADE, related_name='table_rows', verbose_name='Правило')
    form_label = models.CharField('Форма', max_length=100, blank=True)
    pattern = models.CharField('Схема', max_length=300, blank=True)
    example = models.CharField('Пример', max_length=300, blank=True)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'grammar_table_rows'
        ordering = ['rule', 'sort_order']
        verbose_name = 'Строка таблицы'
        verbose_name_plural = 'Строки таблицы'


class GrammarExample(models.Model):
    rule = models.ForeignKey(GrammarRule, on_delete=models.CASCADE, related_name='examples', verbose_name='Правило')
    text_kz = models.TextField('Пример (каз.)')
    text_ru = models.TextField('Перевод', blank=True)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'grammar_examples'
        ordering = ['rule', 'sort_order']
        verbose_name = 'Пример'
        verbose_name_plural = 'Примеры'


class Quiz(Timestamped):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='quizzes', verbose_name='Урок')
    title = models.CharField('Название', max_length=200)
    status = status_field()

    class Meta:
        db_table = 'quizzes'
        ordering = ['lesson', 'id']
        verbose_name = 'Тест'
        verbose_name_plural = 'Тесты'

    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    class Type(models.TextChoices):
        SINGLE = 'single', 'Один ответ'
        MULTIPLE = 'multiple', 'Несколько ответов'
        TEXT = 'text', 'Ввод текста'

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions', verbose_name='Тест')
    question_type = models.CharField('Тип', max_length=10, choices=Type.choices, default=Type.SINGLE)
    prompt = models.TextField('Вопрос')
    explanation = models.TextField('Пояснение к ответу', blank=True)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'quiz_questions'
        ordering = ['quiz', 'sort_order']
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

    def __str__(self):
        return self.prompt


class QuizOption(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='options', verbose_name='Вопрос')
    text = models.CharField('Вариант', max_length=300)
    is_correct = models.BooleanField('Правильный', default=False)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'quiz_options'
        ordering = ['question', 'sort_order']
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответа'

    def __str__(self):
        return self.text


# =====================================================================
#  Админка
# =====================================================================

class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = 'create', 'Создание'
        UPDATE = 'update', 'Изменение'
        DELETE = 'delete', 'Удаление'
        PUBLISH = 'publish', 'Публикация'

    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Кто')
    action = models.CharField('Действие', max_length=10, choices=Action.choices)
    entity_type = models.CharField('Сущность', max_length=30)
    entity_id = models.BigIntegerField('ID сущности', null=True, blank=True)
    changes = models.JSONField('Изменения', default=dict, blank=True)
    created_at = models.DateTimeField('Когда', auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['entity_type', 'entity_id'], name='audit_log_entity_idx')]
        verbose_name = 'Запись журнала'
        verbose_name_plural = 'Журнал изменений'

    def __str__(self):
        return f'{self.get_action_display()} {self.entity_type} #{self.entity_id}'


# =====================================================================
#  Прогресс ученика
# =====================================================================

class PointTransaction(models.Model):
    """Каждое начисление баллов. users.points — их сумма (кэш для рейтинга)."""

    class Reason(models.TextChoices):
        CARD_LEARNED = 'card_learned', '«Я выучил»'
        CARD_AGAIN = 'card_again', '«Учить ещё раз»'
        TOPIC_FIRST = 'topic_first', 'Тема пройдена впервые'
        TOPIC_REPEAT = 'topic_repeat', 'Повторное прохождение'
        QUIZ = 'quiz', 'Тест'
        ADMIN = 'admin', 'Корректировка'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_transactions')
    amount = models.IntegerField('Баллы')
    reason = models.CharField('Причина', max_length=16, choices=Reason.choices)
    source_type = models.CharField('Источник', max_length=20, blank=True)  # card_answer, card_session, quiz_attempt
    source_id = models.BigIntegerField('ID источника', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'point_transactions'
        ordering = ['-created_at']
        verbose_name = 'Начисление баллов'
        verbose_name_plural = 'Начисления баллов'


class UserActivityDay(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_days')
    day = models.DateField()

    class Meta:
        db_table = 'user_activity_days'
        ordering = ['user', 'day']
        constraints = [models.UniqueConstraint(fields=['user', 'day'], name='user_activity_days_uniq')]


class CardResult(models.TextChoices):
    LEARNED = 'learned', 'Я выучил'
    AGAIN = 'again', 'Учить ещё раз'


class UserWordProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='word_progress')
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name='+')
    learned_count = models.PositiveIntegerField(default=0)
    again_count = models.PositiveIntegerField(default=0)
    last_result = models.CharField(max_length=8, choices=CardResult.choices, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_word_progress'
        constraints = [models.UniqueConstraint(fields=['user', 'word'], name='user_word_progress_uniq')]


class UserLessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='+')
    words_read = models.BooleanField(default=False)
    grammar_read = models.BooleanField(default=False)
    text_read = models.BooleanField(default=False)
    cards_completions = models.PositiveIntegerField(default=0)
    quiz_best = models.PositiveSmallIntegerField(default=0)
    first_completed_at = models.DateTimeField(null=True, blank=True)  # первое прохождение карточек
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_lesson_progress'
        constraints = [models.UniqueConstraint(fields=['user', 'lesson'], name='user_lesson_progress_uniq')]


class CardSession(models.Model):
    class Mode(models.TextChoices):
        TOPIC = 'topic', 'Тема'
        REVIEW = 'review', 'Повторение'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='card_sessions')
    mode = models.CharField(max_length=8, choices=Mode.choices, default=Mode.TOPIC)
    module = models.ForeignKey(Module, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    cards_total = models.PositiveSmallIntegerField(default=0)
    learned_count = models.PositiveSmallIntegerField(default=0)
    again_count = models.PositiveSmallIntegerField(default=0)
    points_earned = models.IntegerField(default=0)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'card_sessions'
        ordering = ['-started_at']
        indexes = [models.Index(fields=['user', 'finished_at'], name='card_sessions_user_open_idx')]


class CardAnswer(models.Model):
    session = models.ForeignKey(CardSession, on_delete=models.CASCADE, related_name='answers')
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name='+')
    result = models.CharField(max_length=8, choices=CardResult.choices)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'card_answers'
        ordering = ['session', 'answered_at']


class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    correct_count = models.PositiveSmallIntegerField(default=0)
    total_count = models.PositiveSmallIntegerField(default=0)
    points_earned = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'quiz_attempts'
        ordering = ['-created_at']


class QuizAttemptAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='+')
    option = models.ForeignKey(QuizOption, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    text_answer = models.CharField(max_length=300, blank=True)
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = 'quiz_attempt_answers'
        constraints = [models.UniqueConstraint(fields=['attempt', 'question'], name='quiz_attempt_answers_uniq')]
