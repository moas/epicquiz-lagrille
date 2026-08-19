from django.db import models
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField
from django_fsm import transition

from core.games.models import Episode
from core.games.models import PrizeAttribute
from core.games.models import SpecialAttribute
from core.games.models import StealAttribute
from core.challenges.models import Challenge
from core.helpers.models import BaseModel


class Grid(BaseModel):
    class GridState(models.TextChoices):
        CONFIGURED = "configured", _("Configured")
        POSITIONS_DRAWN = "positions_drawn", _("Cells position")
        ATTRIBUTES_DRAWN = "attributes_drawn", _("Cells attributes")

    episode = models.OneToOneField(
        Episode,
        on_delete=models.CASCADE,
        related_name="grid",
    )
    rows = models.PositiveSmallIntegerField(default=6)
    columns = models.PositiveSmallIntegerField(default=8)
    empty_cell_count = models.PositiveSmallIntegerField(default=8)
    point_distribution = models.JSONField(default=dict)
    state = FSMField(
        choices=GridState.choices,
        default=GridState.CONFIGURED,
        protected=True,
    )

    @property
    def size(self):
        return f"{self.rows} x {self.columns}"

    @property
    def is_ready(self):
        return self.state == self.GridState.ATTRIBUTES_DRAWN

    @transition(
        field=state,
        source=GridState.CONFIGURED,
        target=GridState.POSITIONS_DRAWN,
    )
    def positions_draw(self):
        pass

    @transition(
        field=state,
        source=GridState.POSITIONS_DRAWN,
        target=GridState.ATTRIBUTES_DRAWN,
    )
    def attributes_drawn(self):
        cells = list(self.cells.select_for_update())
        for cell in cells:
            cell.close()
        Cell.objects.bulk_update(cells, ["state"])


class Cell(BaseModel):
    class CellState(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        CLOSED = "CLOSED", _("Closed")
        OPENED = "OPENED", _("Opened")

    grid = models.ForeignKey(Grid, related_name="cells", on_delete=models.CASCADE)
    name = models.CharField(max_length=5, db_index=True, editable=False)
    challenge = models.OneToOneField(
        Challenge,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="cell",
    )
    state = FSMField(
        choices=CellState.choices,
        default=CellState.PENDING,
        protected=True,
    )

    class Meta:
        verbose_name = _("cell")
        verbose_name_plural = _("Cells")

    def __str__(self):
        return f"{self.name} (Grid {self.grid.id.hex[:8]})"

    @property
    def is_blackhole(self):
        return self.challenge is None and self.state != self.CellState.PENDING

    @transition(
        field=state,
        source=CellState.PENDING,
        target=CellState.CLOSED,
    )
    def close(self):
        pass

    @transition(
        field=state,
        source=CellState.CLOSED,
        target=CellState.OPENED,
    )
    def open(self):
        pass


class CellAttribute(BaseModel):
    cell = models.ForeignKey(Cell, on_delete=models.CASCADE, related_name="attributes")
    attribut = models.OneToOneField(
        SpecialAttribute,
        on_delete=models.CASCADE,
        related_name="cell",
    )

    @property
    def is_steal(self):
        attribute = self.attribut.get_real_instance()
        return isinstance(attribute, StealAttribute)

    @property
    def is_prizing(self):
        attribute = self.attribut.get_real_instance()
        return isinstance(attribute, PrizeAttribute)
