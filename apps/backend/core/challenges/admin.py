from django.contrib import admin

from core.challenges.models import Challenge
from core.challenges.models import PlayerResponse


class PlayerResponseInline(admin.TabularInline):
    model = PlayerResponse
    extra = 0
    autocomplete_fields = ("player",)
    readonly_fields = ("state",)


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("id", "episode", "question", "state", "gain", "ttl")
    list_filter = ("state",)
    search_fields = ("id", "episode__title", "question__label")
    autocomplete_fields = ("episode", "question")
    readonly_fields = ("state",)
    inlines = (PlayerResponseInline,)


@admin.register(PlayerResponse)
class PlayerResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "challenge", "player", "score", "state")
    list_filter = ("state",)
    search_fields = ("id", "challenge__question__label", "player__user__username")
    autocomplete_fields = ("challenge", "player")
    readonly_fields = ("state",)
