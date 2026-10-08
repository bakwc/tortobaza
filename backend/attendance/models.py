from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AttendanceEvent(models.Model):
    ARRIVAL = "arrival"
    DEPARTURE = "departure"
    EVENT_TYPE_CHOICES = [
        (ARRIVAL, _("Arrival")),
        (DEPARTURE, _("Departure")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="attendance_events",
        on_delete=models.CASCADE,
        verbose_name=_("User"),
    )
    event_type = models.CharField(
        max_length=10,
        choices=EVENT_TYPE_CHOICES,
        verbose_name=_("Event type"),
    )
    timestamp = models.DateTimeField(default=timezone.now, verbose_name=_("Timestamp"))

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = _("Attendance event")
        verbose_name_plural = _("Attendance events")

    def __str__(self) -> str:
        return f"{self.user} {self.event_type} {self.timestamp}"


class SalaryCalculation(AttendanceEvent):
    class Meta:
        proxy = True
        verbose_name = _("Salary calculation")
        verbose_name_plural = _("Salary calculation")
