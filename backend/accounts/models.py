from decimal import Decimal

from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="profile",
        on_delete=models.CASCADE,
    )
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    telegram_username = models.CharField(max_length=32, blank=True)

    def __str__(self) -> str:
        return f"{self.user} profile"


def chef_identity(user) -> tuple[str, str | None]:
    profile = UserProfile.objects.filter(user=user).first()
    if profile is not None and profile.telegram_username:
        nick = profile.telegram_username.lstrip("@")
        return nick, f"https://t.me/{nick}"
    return user.username, None
