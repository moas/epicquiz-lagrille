from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.helpers.models import BaseModel


class Question(BaseModel):
    class Level(models.IntegerChoices):
        WOOD = 1, _("Wood")
        STONE = 2, _("Stone")
        BRONZE = 3, _("Bronze")
        SILVER = 4, _("Silver")
        GOLD = 5, _("Gold")

    label = models.CharField(_("Question"), max_length=160)
    slug = models.SlugField(max_length=160, db_index=True, unique=True)
    level = models.PositiveSmallIntegerField(
        _("Level"),
        choices=Level.choices,
        default=Level.WOOD,
    )
    tags = ArrayField(
        base_field=models.CharField(max_length=150),
        default=list,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label

    class Meta:
        verbose_name = _("question")
        verbose_name_plural = _("List of questions")
        indexes = [GinIndex(fields=["tags"], name="qa_question_tags_gin")]


class Proposition(BaseModel):
    answer = models.CharField(_("Answer"), max_length=160)
    slug = models.SlugField(max_length=160, db_index=True, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.answer

    class Meta:
        verbose_name = _("proposition")
        verbose_name_plural = _("Question Proposition List")


class Answer(BaseModel):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
        limit_choices_to={"is_active": True},
    )
    proposition = models.ForeignKey(
        Proposition,
        on_delete=models.PROTECT,
        related_name="question_links",
        limit_choices_to={"is_active": True},
    )
    is_correct = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return _("Answer %s") % self.id.hex

    class Meta:
        verbose_name = _("answer")
        verbose_name_plural = _("Answers List")
        constraints = [
            models.UniqueConstraint(
                fields=["question", "proposition"],
                name="qa_unique_question_proposition",
            ),
        ]


class AnswerReason(BaseModel):
    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        related_name="justification",
    )
    content = models.TextField(blank=True)
    metadata = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Justification of question {self.question.id.hex}"

    class Meta:
        verbose_name = _("justification")
        verbose_name_plural = _("Question justification")
