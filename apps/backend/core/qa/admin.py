from django.contrib import admin

from core.qa.models import Answer
from core.qa.models import AnswerReason
from core.qa.models import Proposition
from core.qa.models import Question


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 1
    autocomplete_fields = ("proposition",)


class AnswerReasonInline(admin.StackedInline):
    model = AnswerReason
    extra = 1
    max_num = 1


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("label", "level", "is_active")
    list_filter = ("level", "is_active")
    search_fields = ("label", "slug")
    prepopulated_fields = {"slug": ("label",)}
    inlines = (AnswerInline, AnswerReasonInline)


@admin.register(Proposition)
class PropositionAdmin(admin.ModelAdmin):
    list_display = ("answer", "is_active")
    list_filter = ("is_active",)
    search_fields = ("answer", "slug")
    prepopulated_fields = {"slug": ("answer",)}


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("proposition", "question", "is_correct", "is_active")
    list_filter = ("is_correct", "is_active")
    search_fields = ("question__label", "proposition__answer")
    autocomplete_fields = ("question", "proposition")
