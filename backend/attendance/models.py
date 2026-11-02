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


class ScheduleDay(models.Model):
    WORK = "work"
    OFF = "off"
    VACATION = "vacation"
    SICK = "sick"
    DAY_TYPE_CHOICES = [
        (WORK, _("Work")),
        (OFF, _("Day off")),
        (VACATION, _("Vacation")),
        (SICK, _("Sick leave")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="schedule_days",
        on_delete=models.CASCADE,
        verbose_name=_("User"),
    )
    date = models.DateField(verbose_name=_("Date"))
    day_type = models.CharField(
        max_length=10,
        choices=DAY_TYPE_CHOICES,
        verbose_name=_("Day type"),
    )

    class Meta:
        ordering = ["date", "user_id"]
        verbose_name = _("Schedule day")
        verbose_name_plural = _("Schedule days")
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="unique_schedule_day"),
        ]

    def __str__(self) -> str:
        return f"{self.user} {self.date} {self.day_type}"


class SalaryCalculation(AttendanceEvent):
    class Meta:
        proxy = True
        verbose_name = _("Salary calculation")
        verbose_name_plural = _("Salary calculation")


class SalaryPayout(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="salary_payouts",
        on_delete=models.PROTECT,
        verbose_name=_("User"),
    )
    period_start = models.DateField(verbose_name=_("Start"))
    period_end = models.DateField(verbose_name=_("End"))
    financial_transaction = models.OneToOneField(
        "crm.FinancialTransaction",
        related_name="salary_payout",
        on_delete=models.CASCADE,
        verbose_name=_("Financial transaction"),
    )

    class Meta:
        verbose_name = _("Salary payout")
        verbose_name_plural = _("Salary payouts")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "period_start", "period_end"],
                name="unique_salary_payout_period",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.period_start} {self.period_end}"
