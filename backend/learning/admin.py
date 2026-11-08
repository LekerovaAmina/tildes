from django import forms
from django.contrib import admin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.forms.models import model_to_dict
from django.utils import timezone

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
    PointTransaction,
    Quiz,
    QuizOption,
    QuizQuestion,
    Status,
    Text,
    User,
    Word,
)

admin.site.site_title = 'Tildes'
admin.site.index_title = 'Контент и ученики'


def _jsonable(data):
    return {k: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v)) for k, v in data.items()}


def write_audit(user, action, obj, changes=None):
    AuditLog.objects.create(
        actor=user if user and user.is_authenticated else None,
        action=action,
        entity_type=obj._meta.db_table[:30],
        entity_id=obj.pk,
        changes=changes or {},
    )


class AuditedAdmin(admin.ModelAdmin):
    """Записывает создание, изменение, удаление и публикацию в audit_log; ставит автора и даты публикации."""

    def save_model(self, request, obj, form, change):
        fields = {f.name for f in obj._meta.fields}
        if not change and 'created_by' in fields and obj.created_by_id is None:
            obj.created_by = request.user
        if 'updated_by' in fields:
            obj.updated_by = request.user
        becomes_published = (
            'status' in fields and obj.status == Status.PUBLISHED and 'status' in (form.changed_data if change else ['status'])
        )
        if becomes_published and 'published_at' in fields and obj.published_at is None:
            obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)

        if change:
            diff = {name: [str(form.initial.get(name)), str(form.cleaned_data.get(name))] for name in form.changed_data}
            if diff:
                write_audit(request.user, AuditLog.Action.UPDATE, obj, diff)
        else:
            write_audit(request.user, AuditLog.Action.CREATE, obj, _jsonable(model_to_dict(obj)))
        if becomes_published and change:
            write_audit(request.user, AuditLog.Action.PUBLISH, obj)

    def delete_model(self, request, obj):
        write_audit(request.user, AuditLog.Action.DELETE, obj, {'repr': str(obj)})
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            write_audit(request.user, AuditLog.Action.DELETE, obj, {'repr': str(obj)})
        super().delete_queryset(request, queryset)


# ---------- Пользователи ----------

class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput, required=False,
                                help_text='Оставьте пустым — пользователь не сможет войти по паролю.')

    class Meta:
        model = User
        fields = ['email', 'display_name', 'role']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'] or None)
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(label='Пароль', help_text='Сменить: manage.py changepassword <email>')

    class Meta:
        model = User
        fields = '__all__'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ['email', 'display_name', 'role', 'current_level', 'points', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'current_level']
    search_fields = ['email', 'display_name']
    readonly_fields = ['points', 'date_joined', 'last_login']
    fields = ['email', 'password', 'display_name', 'role', 'current_level', 'points',
              'is_active', 'is_superuser', 'date_joined', 'last_login']

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs['form'] = self.add_form
            kwargs['fields'] = ['email', 'password1', 'display_name', 'role']
        return super().get_form(request, obj, **kwargs)

    def get_fields(self, request, obj=None):
        return ['email', 'password1', 'display_name', 'role'] if obj is None else self.fields

    def get_readonly_fields(self, request, obj=None):
        return [] if obj is None else self.readonly_fields


# ---------- Контент ----------

@admin.register(Level)
class LevelAdmin(AuditedAdmin):
    list_display = ['code', 'title_ru', 'title_kz', 'is_published', 'sort_order']
    list_editable = ['is_published', 'sort_order']


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ['code', 'title_kz', 'title_ru', 'sort_order', 'status']
    show_change_link = True


@admin.register(Module)
class ModuleAdmin(AuditedAdmin):
    list_display = ['number', 'title_kz', 'title_ru', 'level', 'status', 'published_at']
    list_filter = ['level', 'status']
    search_fields = ['title_kz', 'title_ru']
    readonly_fields = ['created_by', 'created_at', 'updated_at', 'published_at']
    inlines = [LessonInline]


class LessonBlockInline(admin.TabularInline):
    model = LessonBlock
    extra = 0


class WordInline(admin.TabularInline):
    model = Word
    extra = 1
    fields = ['sort_order', 'kz', 'ru', 'transcription', 'part_of_speech', 'status']


class TextInline(admin.StackedInline):
    model = Text
    extra = 0
    fields = ['title', 'body', 'translation_ru', 'audio', 'status']


@admin.register(Lesson)
class LessonAdmin(AuditedAdmin):
    list_display = ['code', 'title_kz', 'module', 'status', 'updated_at']
    list_filter = ['module__level', 'module', 'status']
    search_fields = ['title_kz', 'title_ru', 'code']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at', 'published_at']
    inlines = [LessonBlockInline, WordInline, TextInline]


@admin.register(Word)
class WordAdmin(AuditedAdmin):
    list_display = ['kz', 'ru', 'lesson', 'status']
    list_filter = ['lesson__module__level', 'lesson__module', 'status']
    search_fields = ['kz', 'ru']
    raw_id_fields = ['image', 'audio']


@admin.register(Text)
class TextAdmin(AuditedAdmin):
    list_display = ['title', 'lesson', 'status']
    list_filter = ['status']
    search_fields = ['title', 'body']


class GrammarTableRowInline(admin.TabularInline):
    model = GrammarTableRow
    extra = 1


class GrammarExampleInline(admin.TabularInline):
    model = GrammarExample
    extra = 1


@admin.register(GrammarRule)
class GrammarRuleAdmin(AuditedAdmin):
    list_display = ['title_kz', 'title_ru', 'lesson', 'status']
    list_filter = ['status']
    inlines = [GrammarTableRowInline, GrammarExampleInline]


class QuizQuestionInline(admin.StackedInline):
    model = QuizQuestion
    extra = 0
    show_change_link = True


@admin.register(Quiz)
class QuizAdmin(AuditedAdmin):
    list_display = ['title', 'lesson', 'status']
    list_filter = ['status']
    inlines = [QuizQuestionInline]


class QuizOptionInline(admin.TabularInline):
    model = QuizOption
    extra = 1


@admin.register(QuizQuestion)
class QuizQuestionAdmin(AuditedAdmin):
    list_display = ['prompt', 'quiz', 'question_type', 'sort_order']
    list_filter = ['question_type']
    inlines = [QuizOptionInline]


@admin.register(MediaFile)
class MediaFileAdmin(AuditedAdmin):
    list_display = ['file', 'kind', 'mime_type', 'size_bytes', 'uploaded_by', 'created_at']
    list_filter = ['kind']
    readonly_fields = ['size_bytes', 'uploaded_by', 'created_at']

    def save_model(self, request, obj, form, change):
        if obj.uploaded_by_id is None:
            obj.uploaded_by = request.user
        upload = form.cleaned_data.get('file')
        if upload is not None and getattr(upload, 'content_type', None):
            obj.mime_type = upload.content_type
            obj.size_bytes = upload.size
        super().save_model(request, obj, form, change)


# ---------- Журнал и баллы (только чтение) ----------

class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyAdmin):
    list_display = ['created_at', 'actor', 'action', 'entity_type', 'entity_id']
    list_filter = ['action', 'entity_type']
    search_fields = ['entity_type']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PointTransaction)
class PointTransactionAdmin(ReadOnlyAdmin):
    list_display = ['created_at', 'user', 'amount', 'reason', 'source_type', 'source_id']
    list_filter = ['reason']
    search_fields = ['user__email', 'user__display_name']
