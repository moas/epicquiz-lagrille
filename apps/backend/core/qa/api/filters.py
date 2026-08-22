from django.db.models import CharField
from django.db.models import Func
from django.db.models import Q
from django.db.models import Value
from django_filters import rest_framework as filters

from core.qa.models import Question


class QuestionFilter(filters.FilterSet):
    search = filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.annotate(
            tags_as_text=Func(
                "tags",
                Value(" "),
                function="array_to_string",
                output_field=CharField(),
            ),
        ).filter(
            Q(label__icontains=value) | Q(tags_as_text__icontains=value),
        )

    class Meta:
        model = Question
        fields = {
            "level": ["exact"],
            "is_active": ["exact"],
        }
