from pathlib import Path

from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers

from core.qa.models import Answer
from core.qa.models import AnswerReason
from core.qa.models import Proposition
from core.qa.models import Question


class QuestionImportSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False)

    def validate_file(self, value):
        if Path(value.name).suffix.lower() not in {".yaml", ".yml"}:
            message = "Only YAML files are supported."
            raise serializers.ValidationError(message)
        return value


class AnswerSerializer(serializers.ModelSerializer):
    answer = serializers.CharField(source="proposition.answer", read_only=True)

    class Meta:
        model = Answer
        fields = ["id", "answer", "is_correct"]


class PropositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposition
        fields = ["id", "answer", "is_active"]
        read_only_fields = ["id"]


class QuestionSerializer(serializers.ModelSerializer):
    question = serializers.CharField(source="label")
    answers = AnswerSerializer(many=True, read_only=True)
    reason = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ["id", "question", "level", "tags", "reason", "answers", "is_active"]
        read_only_fields = ["id", "answers"]

    @staticmethod
    def get_reason(question):
        try:
            return question.justification.content
        except AnswerReason.DoesNotExist:
            return None


class AnswerInputSerializer(serializers.Serializer):
    answer = serializers.CharField(max_length=160)
    is_correct = serializers.BooleanField(default=False)


class QuestionCreateSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=160)
    level = serializers.ChoiceField(choices=Question.Level.choices)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        default=list,
    )
    reason = serializers.CharField(required=False, allow_blank=True)
    answers = AnswerInputSerializer(many=True, min_length=1)

    @transaction.atomic
    def create(self, validated_data):
        label = validated_data["question"].strip()
        slug = slugify(label)
        if Question.objects.filter(slug=slug).exists():
            raise serializers.ValidationError(
                {"question": "This question already exists."},
            )

        question = Question.objects.create(
            label=label,
            slug=slug,
            level=validated_data["level"],
            tags=list(dict.fromkeys(validated_data["tags"])),
        )
        if "reason" in validated_data:
            AnswerReason.objects.create(
                question=question,
                content=validated_data["reason"],
            )

        for answer_data in validated_data["answers"]:
            proposition, _ = Proposition.objects.get_or_create(
                slug=slugify(answer_data["answer"]),
                defaults={"answer": answer_data["answer"]},
            )
            Answer.objects.get_or_create(
                question=question,
                proposition=proposition,
                defaults={"is_correct": answer_data["is_correct"]},
            )
        return question


class QuestionPropositionSerializer(AnswerInputSerializer):
    @transaction.atomic
    def create(self, validated_data):
        question = self.context["question"]
        proposition, _ = Proposition.objects.get_or_create(
            slug=slugify(validated_data["answer"]),
            defaults={"answer": validated_data["answer"]},
        )
        answer, _ = Answer.objects.get_or_create(
            question=question,
            proposition=proposition,
            defaults={"is_correct": validated_data["is_correct"]},
        )
        return answer
