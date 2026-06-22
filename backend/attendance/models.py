from django.conf import settings
from django.db import models
from django.utils import timezone


class AttendanceEvent(models.Model):
    ARRIVAL = "arrival"
    DEPARTURE = "departure"
    EVENT_TYPE_CHOICES = [
        (ARRIVAL, "Arrival"),
        (DEPARTURE, "Departure"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="attendance_events",
        on_delete=models.CASCADE,
    )
    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.user} {self.event_type} {self.timestamp}"


class SalaryCalculation(AttendanceEvent):
    class Meta:
        proxy = True
        verbose_name = "Salary calculation"
        verbose_name_plural = "Salary calculation"
