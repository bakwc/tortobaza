from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    GENDER_MALE = "male"
    GENDER_FEMALE = "female"
    GENDER_CHOICES = [
        (GENDER_MALE, _("Male")),
        (GENDER_FEMALE, _("Female")),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="profile",
        on_delete=models.CASCADE,
        verbose_name=_("User"),
    )
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Hourly rate"),
    )
    telegram_username = models.CharField(max_length=32, blank=True, verbose_name=_("Telegram username"))
    internal_name = models.CharField(max_length=64, blank=True, verbose_name=_("Internal name"))
    gender = models.CharField(
        max_length=6,
        choices=GENDER_CHOICES,
        default=GENDER_FEMALE,
        verbose_name=_("Gender"),
    )

    class Meta:
        verbose_name = _("Profile")
        verbose_name_plural = _("Profiles")

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
