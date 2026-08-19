from enum import unique, auto

from django.utils.translation import gettext_lazy as _

from core.helpers.functional import AutoName


@unique
class ChallengeState(AutoName):
    PENDING = auto()
    OPENED = auto()
    CLOSED = auto()


ChallengeStateChoices = (
    (ChallengeState.PENDING.value, _('PENDING')),
    (ChallengeState.OPENED.value, _('OPENED')),
    (ChallengeState.CLOSED.value, _('CLOSED')),
)


@unique
class UserResponseState(AutoName):
    PENDING = auto()
    SUBMIT = auto()
    OUTDATED = auto()
    SKIPPED = auto()
    SUCCEEDED = auto()
    FAILED = auto()


UserResponseStateChoices = (
    (UserResponseState.PENDING.value, _('PENDING')),
    (UserResponseState.SUBMIT.value, _('SUBMIT')),
    (UserResponseState.OUTDATED.value, _('OUTDATED')),
    (UserResponseState.SUCCEEDED.value, _('SUCCEEDED')),
    (UserResponseState.FAILED.value, _('FAILED')),
    (UserResponseState.SKIPPED.value, _('SKIPPED')),
)
