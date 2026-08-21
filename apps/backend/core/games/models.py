from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField
from django_fsm import transition
from model_utils import FieldTracker
from model_utils.models import TimeFramedModel
from polymorphic.models import PolymorphicModel

from core.helpers.models import BaseModel


class Episode(BaseModel, TimeFramedModel):
    """Game model."""

    class State(models.TextChoices):
        PENDING = "pending", _("Pending")
        START = "start", _("Started")
        END = "end", _("Ended")

    title = models.CharField(max_length=255, verbose_name=_("Title"))
    time_slot = models.PositiveSmallIntegerField(
        _("Default game timespan"),
        default=10,
        validators=[MinValueValidator(1)],
        help_text=_("Base of timespan for current game (seconds)"),
    )
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    state = FSMField(
        choices=State.choices,
        default=State.PENDING,
        protected=True,
    )

    tracker = FieldTracker(fields=("is_active",))

    def __str__(self):
        return self.title

    def has_grid(self):
        return hasattr(self, "grid")

    @transition(
        field=state,
        source=State.PENDING,
        target=State.START,
        conditions=[has_grid],
    )
    def start(self):
        self.start = timezone.now()

    @transition(field=state, source=State.START, target=State.END)
    def end(self):
        self.end = timezone.now()

    class Meta:
        verbose_name = _("Game")
        verbose_name_plural = _("Games")
        ordering = ("title",)


class Participant(BaseModel):

    class Role(models.TextChoices):
        PLAYER = "PLAYER", _("Player")
        SCREEN = "SCREEN", _("Screen")
        PRESENTER = "PRESENTER", _("Presenter")
        OPERATOR = "OPERATOR", _("Operator")

    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name="participants")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='game_participant')
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    is_active = models.BooleanField(default=True)
    tags = ArrayField(
        base_field=models.CharField(max_length=150),
        help_text=_("Tags list"),
        blank=True, null=True,
    )

    def __str__(self):
        return f"Ep. {self.episode.title}: {self.role}"

    class Meta:
        verbose_name = _("participant")
        verbose_name_plural = _("Participants")


class QueryConfig(BaseModel):

    class Join(models.TextChoices):
        OR = "or",  _("OR")
        AND = "and", _("AND")

    class Mode(models.TextChoices):
        SELECT = "select", _("Select")
        UNSELECT = "unselect", _("Unselect")

    episode = models.ForeignKey(
        Episode,
        limit_choices_to={"is_active": True},
        on_delete=models.CASCADE,
        related_name="queries_config",
    )
    join = models.CharField(max_length=3, choices=Join.choices, default=Join.AND)
    mode = models.CharField(max_length=8, choices=Mode.choices)
    tags = ArrayField(
        base_field=models.CharField(max_length=150),
        help_text=_("Tags list"),
        blank=True, null=True,
    )
    level = ArrayField(
        base_field=models.PositiveSmallIntegerField(),
        help_text=_("Question level"),
        blank=True, null=True,
    )

    def __str__(self):
        return _("Queries conf for episode: %s...") % self.episode.id.hex[:8]

    class Meta:
        verbose_name = _("Query conf")
        verbose_name_plural = _("Queries conf")
        ordering = ("id",)

    @property
    def query(self):
        params = {}
        if self.tags:
            q = "tags__contains"
            params.update({q: self.tags})
        if self.level:
            q = "level__in"
            params.update({q: self.level})

        if self.mode == self.Mode.SELECT:
            return models.Q(**params)
        return ~models.Q(**params)


class SpecialAttribute(PolymorphicModel, BaseModel):
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name="special_attributes")
    is_active = models.BooleanField(default=True)


class StealAttribute(SpecialAttribute):
    pass


class PrizeAttribute(SpecialAttribute):
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='prizes')
