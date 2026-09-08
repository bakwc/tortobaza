from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from attendance.models import AttendanceEvent

_TB = ZoneInfo("Asia/Tbilisi")


def _event(user: User, event_type: str, day: date, hour: int, minute: int) -> AttendanceEvent:
    return AttendanceEvent.objects.create(
        user=user,
        event_type=event_type,
        timestamp=timezone.make_aware(
            datetime(day.year, day.month, day.day, hour, minute),
            _TB,
        ),
    )


class CrmExpensesApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.worker = User.objects.create_user(username="worker", password="password")
        self.admin = User.objects.create_user(username="admin", password="password", is_staff=True)
        UserProfile.objects.create(user=self.worker, hourly_rate=Decimal("10.00"))
        self.day = date(2026, 6, 15)

    def test_unauthenticated_access_denied(self):
        response = self.client.get("/api/crm/expenses/")
        self.assertEqual(response.status_code, 403)

    def test_non_staff_access_denied(self):
        self.client.force_authenticate(user=self.worker)
        response = self.client.get("/api/crm/expenses/")
        self.assertEqual(response.status_code, 403)

    def test_day_salary(self):
        _event(self.worker, AttendanceEvent.ARRIVAL, self.day, 9, 0)
        _event(self.worker, AttendanceEvent.DEPARTURE, self.day, 17, 0)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/expenses/", {"date": "2026-06-15"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"date": "2026-06-15", "salary": "80.00"})

    def test_month_salary(self):
        other = User.objects.create_user(username="other", password="password")
        UserProfile.objects.create(user=other, hourly_rate=Decimal("20.00"))
        day2 = date(2026, 6, 16)
        _event(self.worker, AttendanceEvent.ARRIVAL, self.day, 9, 0)
        _event(self.worker, AttendanceEvent.DEPARTURE, self.day, 17, 0)
        _event(other, AttendanceEvent.ARRIVAL, day2, 10, 0)
        _event(other, AttendanceEvent.DEPARTURE, day2, 14, 0)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/expenses/", {"month": "2026-06"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["month"], "2026-06")
        self.assertEqual(data["salary"], "160.00")
        self.assertEqual(data["by_date"]["2026-06-15"], "80.00")
        self.assertEqual(data["by_date"]["2026-06-16"], "80.00")

    def test_default_today_tbilisi(self):
        today = timezone.now().astimezone(_TB).date()
        _event(self.worker, AttendanceEvent.ARRIVAL, today, 9, 0)
        _event(self.worker, AttendanceEvent.DEPARTURE, today, 17, 0)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/expenses/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["date"], today.isoformat())
        self.assertEqual(data["salary"], "80.00")
