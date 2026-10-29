from django.contrib import admin

from .models import Learner, Level, Module, Question, Word


class WordInline(admin.TabularInline):
    model = Word
    extra = 1


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ['code', 'title_ru', 'title', 'available', 'order']
    list_editable = ['available', 'order']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'title_ru', 'level']
    list_filter = ['level']
    inlines = [WordInline, QuestionInline]


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ['kz', 'ru', 'module']
    list_filter = ['module__level', 'module']
    search_fields = ['kz', 'ru']


@admin.register(Learner)
class LearnerAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'level', 'points', 'created_at']
    readonly_fields = ['device_id', 'created_at']
