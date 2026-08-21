from django.contrib import admin

from core.games.models import Episode
from core.games.models import Participant
from core.games.models import PrizeAttribute
from core.games.models import QueryConfig
from core.games.models import SpecialAttribute
from core.games.models import StealAttribute


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0
    autocomplete_fields = ("user",)


class QueryConfigInline(admin.TabularInline):
    model = QueryConfig
    extra = 0


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ("title", "state", "time_slot", "is_active")
    list_filter = ("state", "is_active")
    search_fields = ("title",)
    readonly_fields = ("state",)
    inlines = (ParticipantInline, QueryConfigInline)


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("user", "episode", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("user__username", "user__email", "episode__title")
    autocomplete_fields = ("episode", "user")


@admin.register(QueryConfig)
class QueryConfigAdmin(admin.ModelAdmin):
    list_display = ("episode", "join", "mode")
    list_filter = ("join", "mode")
    search_fields = ("episode__title",)
    autocomplete_fields = ("episode",)


@admin.register(SpecialAttribute)
class SpecialAttributeAdmin(admin.ModelAdmin):
    list_display = ("id", "episode", "is_active")
    list_filter = ("is_active",)
    search_fields = ("episode__title",)
    autocomplete_fields = ("episode",)


@admin.register(StealAttribute)
class StealAttributeAdmin(admin.ModelAdmin):
    list_display = ("id", "episode", "is_active")
    list_filter = ("is_active",)
    search_fields = ("episode__title",)
    autocomplete_fields = ("episode",)


@admin.register(PrizeAttribute)
class PrizeAttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "episode", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "episode__title")
    autocomplete_fields = ("episode",)
