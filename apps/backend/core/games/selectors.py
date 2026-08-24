"""Read models for preparing an episode question pool."""

from django.db.models import Q

from core.qa.models import Question


def eligible_questions_for_episode(episode):
    """Return active questions allowed by an episode's query configuration."""
    select_query = Q()
    exclude_query = Q()
    has_select_rule = False

    for config in episode.queries_config.all():
        if config.mode == config.Mode.SELECT:
            select_query |= config.query
            has_select_rule = True
        else:
            exclude_query |= ~config.query

    if not has_select_rule:
        return Question.objects.none()

    queryset = Question.objects.filter(is_active=True).filter(select_query)
    return queryset.exclude(exclude_query).prefetch_related("answers__proposition")
