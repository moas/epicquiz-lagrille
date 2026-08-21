from django_filters import rest_framework as filters

from core.games.models import Episode


class EpisodeFilter(filters.FilterSet):
    search = filters.CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        model = Episode
        fields = {
            "state": ["exact"],
            "is_active": ["exact"],
        }
