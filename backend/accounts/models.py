from decimal import Decimal

from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    GENDER_MALE = "male"
    GENDER_FEMALE = "female"
    GENDER_CHOICES = [
        (GENDER_MALE, "Male"),
        (GENDER_FEMALE, "Female"),
    ]

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
    internal_name = models.CharField(max_length=64, blank=True)
    gender = models.CharField(
        max_length=6,
        choices=GENDER_CHOICES,
        default=GENDER_FEMALE,
    )

    def __str__(self) -> str:
        return f"{self.user} profile"


def chef_identity(user) -> tuple[str, str | None, str | None, str]:
    profile = UserProfile.objects.filter(user=user).first()
    if profile is None:
        return user.username, None, None, UserProfile.GENDER_FEMALE
    telegram_nick = None
    telegram_url = None
    if profile.telegram_username:
        telegram_nick = profile.telegram_username.lstrip("@")
        telegram_url = f"https://t.me/{telegram_nick}"
    if profile.internal_name:
        display_name = profile.internal_name
    elif telegram_nick is not None:
        display_name = telegram_nick
    else:
        display_name = user.username
    return display_name, telegram_url, telegram_nick, profile.gender
