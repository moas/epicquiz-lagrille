from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import TextChoices
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom user model."""

    class PresenceStatus(TextChoices):
        OK = "ok", _("OK")
        WARNING = "warning", _("Warning")
        CRITICAL = "critical", _("Critical")

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    last_ping = DateTimeField(blank=True, null=True)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    @property
    def presence_status(self):
        """Return the account presence derived from its most recent ping."""

        if not hasattr(self, "game_participant"):
            return None

        if self.last_ping is None:
            return (
                self.PresenceStatus.CRITICAL
                if hasattr(self, "auth_token")
                else self.PresenceStatus.OK
            )

        elapsed = timezone.now() - self.last_ping
        if elapsed > timedelta(minutes=1):
            return self.PresenceStatus.CRITICAL
        if elapsed >= timedelta(seconds=30):
            return self.PresenceStatus.WARNING
        return self.PresenceStatus.OK
