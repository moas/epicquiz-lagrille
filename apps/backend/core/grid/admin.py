from django.contrib import admin

from core.grid.models import Cell
from core.grid.models import CellAttribute
from core.grid.models import Grid


class CellInline(admin.TabularInline):
    model = Cell
    extra = 0
    fields = ("name", "x", "y", "challenge", "state")
    readonly_fields = ("name", "x", "y", "state")
    autocomplete_fields = ("challenge",)


@admin.register(Grid)
class GridAdmin(admin.ModelAdmin):
    list_display = ("episode", "size", "empty_cell_count", "state", "is_ready")
    list_filter = ("state",)
    search_fields = ("episode__title",)
    autocomplete_fields = ("episode",)
    readonly_fields = ("state", "size", "is_ready")
    inlines = (CellInline,)


@admin.register(Cell)
class CellAdmin(admin.ModelAdmin):
    list_display = ("name", "grid", "x", "y", "challenge", "state")
    list_filter = ("state",)
    search_fields = ("name", "grid__episode__title")
    autocomplete_fields = ("grid", "challenge")
    readonly_fields = ("name", "x", "y", "state")


@admin.register(CellAttribute)
class CellAttributeAdmin(admin.ModelAdmin):
    list_display = ("cell", "attribut")
    search_fields = ("cell__name", "cell__grid__episode__title")
    autocomplete_fields = ("cell", "attribut")
