"""Asynchronous audit-report exports."""

from __future__ import annotations

from importlib import import_module

from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from .services import build_report
from .services import render_csv
from .services import render_json
from .services import render_pdf


@shared_task
def generate_audit_report(episode_id: int, format: str) -> str:  # noqa: A002
    """Generate and store a report; return its storage name for download wiring."""
    renderers = {"csv": render_csv, "json": render_json, "pdf": render_pdf}
    try:
        renderer = renderers[format]
    except KeyError as error:
        message = f"Unsupported audit report format: {format}"
        raise ValueError(message) from error

    episode_model, event_model = _game_models()
    episode = episode_model.objects.prefetch_related("participants__user").get(
        pk=episode_id,
    )
    events = event_model.objects.filter(episode=episode).order_by("sequence")
    content = renderer(build_report(episode, events))
    return default_storage.save(
        f"audit-reports/episode-{episode_id}.{format}",
        ContentFile(content),
    )


def _game_models():
    """Delay the dependency until the game domain provides its event log models."""
    models = import_module("core.games.models")
    return models.Episode, models.GameEvent
