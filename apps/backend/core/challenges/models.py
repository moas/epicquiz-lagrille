from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.timezone import timedelta, now
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, transition
from model_utils import FieldTracker

from core.helpers.models import BaseModel
from core.games.models import Episode, Participant
from core.qa.models import Question

from .fsm import (
    ChallengeState, ChallengeStateChoices,
    UserResponseState, UserResponseStateChoices
)


class Challenge(BaseModel):
    episode = models.ForeignKey(
        Episode,
        on_delete=models.CASCADE,
        related_name='challenges',
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,
        related_name='challenges',
        limit_choices_to={'is_active': True}
    )
    proposals = ArrayField(models.UUIDField())  # question answers list sent to player
    ok_answers = ArrayField(models.UUIDField())  # good response expected
    access = ArrayField(models.CharField(max_length=8), null=True, blank=True)  # challenge affected
    timespan = models.PositiveIntegerField(
        default=10,
        help_text=_('Time available to send a reply (seconds)'),
        validators=[MinValueValidator(1)],
    )
    gain = models.PositiveSmallIntegerField(default=0, help_text=_("Point to gain in case of success"))
    ttl = models.DateTimeField(null=True, blank=True)
    state = FSMField(
        default=ChallengeState.PENDING.value,
        choices=ChallengeStateChoices,
        db_index=True,
        protected=True,
    )
    tags = ArrayField(models.CharField(max_length=20), blank=True, null=True)
    tracker = FieldTracker(fields=('state', 'ttl'))

    def __str__(self):
        return _('Challenge %s') % self.id.hex

    class Meta:
        verbose_name = _('challenge')
        verbose_name_plural = _('Challenges list')

    def _compute_and_set_ttl(self, extra):
        if self.timespan <= 0:
            return
        ttl = now() + timedelta(seconds=(self.timespan + extra))
        self.ttl = ttl

    @transition(
        field=state,
        source=ChallengeState.PENDING.value,
        target=ChallengeState.OPENED.value
    )
    def opened(self, extra=1):
        self._compute_and_set_ttl(extra)

    @transition(
        field=state,
        source='*',
        target=ChallengeState.CLOSED.value
    )
    def closed(self):
        pass


class PlayerResponse(BaseModel):
    player = models.ForeignKey(
        Participant,
        related_name='responses',
        on_delete=models.CASCADE,
    )
    challenge = models.ForeignKey(
        Challenge,
        related_name='responses',
        on_delete=models.CASCADE
    )
    answers = ArrayField(models.UUIDField(), null=True)
    score = models.SmallIntegerField(default=0)
    state = FSMField(
        default=UserResponseState.PENDING.value,
        choices=UserResponseStateChoices,
        db_index=True,
        protected=True,
    )
    tracker = FieldTracker(fields=('state',))

    def __str__(self):
        return _('Response %s') % self.id.hex

    def clean(self):
        super().clean()

        if not self.player_id or not self.challenge_id:
            return  # les champs requis sont validés par Django

        errors = {}

        if self.player.role != Participant.Role.PLAYER:
            errors["player"] = "Only a player can respond."

        if not self.player.is_active:
            errors["player"] = "Inactive players cannot respond."

        if self.player.episode_id != self.challenge.game_id:
            errors["player"] = "The player does not belong to this challenge episode."

        if self.answers is not None:
            proposal_ids = set(self.challenge.proposals)
            unknown_answers = set(self.answers) - proposal_ids
            if unknown_answers:
                errors["answers"] = "Answers must be proposals from this challenge."

        if errors:
            raise ValidationError(errors)

    class Meta:
        verbose_name = _('response')
        verbose_name_plural = _('Players responses')

    @transition(
        field=state,
        source=UserResponseState.PENDING.value,
        target=UserResponseState.OUTDATED.value,
    )
    def outdated(self):
        pass

    @transition(
        field=state,
        source=UserResponseState.PENDING.value,
        target=UserResponseState.SKIPPED.value
    )
    def skipped(self):
        pass

    @transition(
        field=state,
        source=UserResponseState.PENDING.value,
        target=UserResponseState.SUBMIT.value,
    )
    def submit(self):
        pass

    @transition(
        field=state,
        source=UserResponseState.SUBMIT.value,
        target=UserResponseState.SUCCEEDED.value
    )
    def succeeded(self):
        pass

    @transition(
        field=state,
        source=UserResponseState.SUBMIT.value,
        target=UserResponseState.FAILED.value
    )
    def failed(self):
        pass

    @transition(
        field=state,
        source=UserResponseState.FAILED.value,
        target=UserResponseState.PENDING.value
    )
    def pending(self):
        """to give another opportunity"""
        pass
