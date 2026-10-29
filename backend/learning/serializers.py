from rest_framework import serializers

from .models import Level, Module, Question, Word


class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ['code', 'title', 'title_ru', 'description', 'available']


class WordSerializer(serializers.ModelSerializer):
    module_id = serializers.IntegerField(source='module.id', read_only=True)

    class Meta:
        model = Word
        fields = ['id', 'kz', 'ru', 'module_id']


class QuestionSerializer(serializers.ModelSerializer):
    # Правильный ответ не отдаём — проверка на сервере (POST /api/modules/<id>/quiz/)
    class Meta:
        model = Question
        fields = ['id', 'text', 'options']


class ModuleShortSerializer(serializers.ModelSerializer):
    word_count = serializers.IntegerField(source='words.count', read_only=True)
    question_count = serializers.IntegerField(source='questions.count', read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'number', 'title', 'title_ru', 'emoji', 'color', 'lessons', 'word_count', 'question_count']


class ModuleDetailSerializer(serializers.ModelSerializer):
    words = WordSerializer(many=True, read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    text = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ['id', 'number', 'title', 'title_ru', 'emoji', 'color', 'lessons', 'words', 'grammar', 'text', 'questions']

    def get_text(self, obj):
        return {'title': obj.text_title, 'paragraphs': obj.text_paragraphs}


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
    name = serializers.CharField(max_length=60, required=False, allow_blank=True)
    level = serializers.CharField(max_length=4, required=False)
