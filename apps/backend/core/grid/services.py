"""Transactional commands for the grid lifecycle."""

from __future__ import annotations

import random
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from core.games.models import SpecialAttribute

from .models import CellAttribute
from .models import Grid


@transaction.atomic
def draw_attributes(grid_id: Any) -> Grid:
    """Assign active attributes to challenge cells and close the grid atomically."""
    grid = Grid.objects.select_for_update().get(pk=grid_id)
    candidate_cell_ids = list(
        grid.cells.select_for_update()
        .filter(challenge__isnull=False)
        .values_list("pk", flat=True),
    )
    attribute_ids = list(
        SpecialAttribute.objects.select_for_update()
        .filter(episode=grid.episode, is_active=True)
        .values_list("pk", flat=True),
    )

    if len(attribute_ids) > len(candidate_cell_ids):
        message = "More active attributes than cells containing a challenge."
        raise ValidationError(message)

    selected_cell_ids = random.SystemRandom().sample(
        candidate_cell_ids,
        k=len(attribute_ids),
    )
    CellAttribute.objects.bulk_create(
        [
            CellAttribute(cell_id=cell_id, attribut_id=attribute_id)
            for cell_id, attribute_id in zip(
                selected_cell_ids,
                attribute_ids,
                strict=True,
            )
        ],
    )

    grid.attributes_drawn()
    grid.save(update_fields=["state", "modified"])
    return grid
