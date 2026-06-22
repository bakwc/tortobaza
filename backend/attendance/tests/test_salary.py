from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from attendance.models import AttendanceEvent
from attendance.salary import compute_day_worked_seconds, compute_salary

_TB = ZoneInfo("Asia/Tbilisi")


def _dt(day: date, hour: int, minute: int, second: int = 0) -> datetime:
    return timezone.make_aware(
        datetime(day.year, day.month, day.day, hour, minute, second),
        _TB,
    )


def _event(
    user: User,
    event_type: str,
    day: date,
    hour: int,
    minute: int,
    second: int = 0,
) -> AttendanceEvent:
    return AttendanceEvent.objects.create(
        user=user,
        event_type=event_type,
        timestamp=_dt(day, hour, minute, second),
    )


class ComputeDayWorkedSecondsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="worker", password="pass")
        self.day = date(2026, 6, 15)

    def test_simple_arrival_departure(self):
        events = [
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.ARRIVAL,
                timestamp=_dt(self.day, 9, 0),
            ),
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.DEPARTURE,
                timestamp=_dt(self.day, 17, 0),
            ),
        ]
        self.assertEqual(compute_day_worked_seconds(events), 8 * 3600)

    def test_midday_gap(self):
        events = [
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.ARRIVAL,
                timestamp=_dt(self.day, 9, 0),
            ),
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.DEPARTURE,
                timestamp=_dt(self.day, 13, 0),
            ),
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.ARRIVAL,
                timestamp=_dt(self.day, 14, 0),
            ),
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.DEPARTURE,
                timestamp=_dt(self.day, 18, 0),
            ),
        ]
        self.assertEqual(compute_day_worked_seconds(events), 8 * 3600)

    def test_double_arrival(self):
        events = [
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.ARRIVAL,
                timestamp=_dt(self.day, 9, 0),
            ),
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.ARRIVAL,
                timestamp=_dt(self.day, 9, 30),
            ),
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.DEPARTURE,
                timestamp=_dt(self.day, 17, 0),
            ),
        ]
        self.assertEqual(compute_day_worked_seconds(events), 8 * 3600)

    def test_double_departure(self):
        events = [
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.ARRIVAL,
                timestamp=_dt(self.day, 9, 0),
            ),
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.DEPARTURE,
                timestamp=_dt(self.day, 17, 0),
            ),
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.DEPARTURE,
                timestamp=_dt(self.day, 17, 30),
            ),
        ]
        self.assertEqual(compute_day_worked_seconds(events), 8 * 3600 + 30 * 60)

    def test_leading_departure(self):
        events = [
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.DEPARTURE,
                timestamp=_dt(self.day, 8, 0),
            ),
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.ARRIVAL,
                timestamp=_dt(self.day, 9, 0),
            ),
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.DEPARTURE,
                timestamp=_dt(self.day, 17, 0),
            ),
        ]
        self.assertEqual(compute_day_worked_seconds(events), 8 * 3600)

    def test_trailing_arrival(self):
        events = [
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.ARRIVAL,
                timestamp=_dt(self.day, 9, 0),
            ),
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.DEPARTURE,
                timestamp=_dt(self.day, 17, 0),
            ),
            AttendanceEvent(
                user=self.user,
                event_type=AttendanceEvent.ARRIVAL,
                timestamp=_dt(self.day, 18, 0),
            ),
        ]
        self.assertEqual(compute_day_worked_seconds(events), 8 * 3600)

    def test_empty_day(self):
        self.assertEqual(compute_day_worked_seconds([]), 0)


class ComputeSalaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="worker", password="pass")
        UserProfile.objects.create(user=self.user, hourly_rate=Decimal("10.00"))
        self.day1 = date(2026, 6, 15)
        self.day2 = date(2026, 6, 16)

    def test_simple_day_with_money(self):
        _event(self.user, AttendanceEvent.ARRIVAL, self.day1, 9, 0)
        _event(self.user, AttendanceEvent.DEPARTURE, self.day1, 17, 0)
        result = compute_salary(self.user, self.day1, self.day1)
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["hours"], Decimal("8.00"))
        self.assertEqual(result["rows"][0]["money"], Decimal("80.00"))
        self.assertEqual(result["total_hours"], Decimal("8.00"))
        self.assertEqual(result["total_money"], Decimal("80.00"))

    def test_empty_day_in_range(self):
        result = compute_salary(self.user, self.day1, self.day2)
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(result["rows"][0]["hours"], Decimal("0.00"))
        self.assertEqual(result["rows"][0]["money"], Decimal("0.00"))
        self.assertEqual(result["rows"][1]["hours"], Decimal("0.00"))
        self.assertEqual(result["rows"][1]["money"], Decimal("0.00"))
        self.assertEqual(result["total_hours"], Decimal("0.00"))
        self.assertEqual(result["total_money"], Decimal("0.00"))

    def test_totals_across_multiple_days(self):
        _event(self.user, AttendanceEvent.ARRIVAL, self.day1, 9, 0)
        _event(self.user, AttendanceEvent.DEPARTURE, self.day1, 17, 0)
        _event(self.user, AttendanceEvent.ARRIVAL, self.day2, 10, 0)
        _event(self.user, AttendanceEvent.DEPARTURE, self.day2, 14, 0)
        result = compute_salary(self.user, self.day1, self.day2)
        self.assertEqual(result["rows"][0]["hours"], Decimal("8.00"))
        self.assertEqual(result["rows"][1]["hours"], Decimal("4.00"))
        self.assertEqual(result["total_hours"], Decimal("12.00"))
        self.assertEqual(result["total_money"], Decimal("120.00"))

    def test_sub_hour_money(self):
        _event(self.user, AttendanceEvent.ARRIVAL, self.day1, 9, 0)
        _event(self.user, AttendanceEvent.DEPARTURE, self.day1, 9, 30)
        result = compute_salary(self.user, self.day1, self.day1)
        self.assertEqual(result["rows"][0]["hours"], Decimal("0.50"))
        self.assertEqual(result["rows"][0]["money"], Decimal("5.00"))
        self.assertEqual(result["total_money"], Decimal("5.00"))

    def test_money_uses_per_second_not_rounded_hours(self):
        _event(self.user, AttendanceEvent.ARRIVAL, self.day1, 9, 0)
        _event(self.user, AttendanceEvent.DEPARTURE, self.day1, 9, 10)
        result = compute_salary(self.user, self.day1, self.day1)
        self.assertEqual(result["rows"][0]["money"], Decimal("1.67"))
        self.assertEqual(result["total_money"], Decimal("1.67"))

    def test_money_counts_seconds(self):
        _event(self.user, AttendanceEvent.ARRIVAL, self.day1, 9, 0, 0)
        _event(self.user, AttendanceEvent.DEPARTURE, self.day1, 9, 1, 30)
        result = compute_salary(self.user, self.day1, self.day1)
        self.assertEqual(result["rows"][0]["money"], Decimal("0.25"))
        self.assertEqual(result["total_money"], Decimal("0.25"))
