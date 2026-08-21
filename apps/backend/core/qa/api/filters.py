from django_filters import rest_framework as filters

from core.qa.models import Question


class QuestionFilter(filters.FilterSet):
    search = filters.CharFilter(field_name="label", lookup_expr="icontains")

    class Meta:
        model = Question
        fields = {
            "level": ["exact"],
            "is_active": ["exact"],
        }
