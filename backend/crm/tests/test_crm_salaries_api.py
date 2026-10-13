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


class CrmSalariesApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.worker = User.objects.create_user(username="worker", password="password")
        self.other = User.objects.create_user(username="other", password="password")
        self.idle = User.objects.create_user(username="idle", password="password")
        self.admin = User.objects.create_user(username="admin", password="password", is_staff=True)
        self.staff = User.objects.create_user(username="staff", password="password", is_staff=True)
        UserProfile.objects.create(user=self.admin, is_finance_admin=True)
        UserProfile.objects.create(
            user=self.worker,
            hourly_rate=Decimal("10.00"),
            internal_name="Бека",
        )
        UserProfile.objects.create(
            user=self.other,
            hourly_rate=Decimal("20.00"),
            internal_name="Анна",
        )
        UserProfile.objects.create(
            user=self.idle,
            hourly_rate=Decimal("15.00"),
            internal_name="Илья",
        )

    def test_unauthenticated_access_denied(self):
        response = self.client.get("/api/crm/salaries/", {"month": "2026-06"})
        self.assertEqual(response.status_code, 403)

    def test_non_staff_access_denied(self):
        self.client.force_authenticate(user=self.worker)
        response = self.client.get("/api/crm/salaries/", {"month": "2026-06"})
        self.assertEqual(response.status_code, 403)

    def test_staff_without_finance_admin_denied(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/api/crm/salaries/", {"month": "2026-06"})
        self.assertEqual(response.status_code, 403)

    def test_splits_halves_and_skips_empty(self):
        _event(self.worker, AttendanceEvent.ARRIVAL, date(2026, 6, 10), 9, 0)
        _event(self.worker, AttendanceEvent.DEPARTURE, date(2026, 6, 10), 17, 0)
        _event(self.worker, AttendanceEvent.ARRIVAL, date(2026, 6, 16), 10, 0)
        _event(self.worker, AttendanceEvent.DEPARTURE, date(2026, 6, 16), 14, 0)
        _event(self.other, AttendanceEvent.ARRIVAL, date(2026, 6, 20), 10, 0)
        _event(self.other, AttendanceEvent.DEPARTURE, date(2026, 6, 20), 14, 0)
        _event(self.idle, AttendanceEvent.ARRIVAL, date(2026, 6, 5), 9, 0)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/salaries/", {"month": "2026-06"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "month": "2026-06",
                "periods": [
                    {
                        "start": "2026-06-01",
                        "end": "2026-06-14",
                        "employees": [
                            {
                                "id": self.worker.id,
                                "name": "Бека",
                                "hours": "8.00",
                                "money": "80.00",
                            }
                        ],
                        "total_hours": "8.00",
                        "total_money": "80.00",
                    },
                    {
                        "start": "2026-06-15",
                        "end": "2026-06-30",
                        "employees": [
                            {
                                "id": self.other.id,
                                "name": "Анна",
                                "hours": "4.00",
                                "money": "80.00",
                            },
                            {
                                "id": self.worker.id,
                                "name": "Бека",
                                "hours": "4.00",
                                "money": "40.00",
                            },
                        ],
                        "total_hours": "8.00",
                        "total_money": "120.00",
                    },
                ],
                "total_hours": "16.00",
                "total_money": "200.00",
            },
        )

    def test_february_second_period_ends_on_last_day(self):
        _event(self.worker, AttendanceEvent.ARRIVAL, date(2026, 2, 20), 9, 0)
        _event(self.worker, AttendanceEvent.DEPARTURE, date(2026, 2, 20), 17, 0)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/salaries/", {"month": "2026-02"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["periods"][0]["employees"], [])
        self.assertEqual(data["periods"][0]["total_hours"], "0.00")
        self.assertEqual(data["periods"][1]["end"], "2026-02-28")
        self.assertEqual(data["periods"][1]["employees"][0]["name"], "Бека")
        self.assertEqual(data["total_money"], "80.00")

    def test_default_current_tbilisi_month(self):
        today = timezone.now().astimezone(_TB).date()
        _event(self.worker, AttendanceEvent.ARRIVAL, today, 9, 0)
        _event(self.worker, AttendanceEvent.DEPARTURE, today, 17, 0)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/salaries/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["month"], f"{today.year:04d}-{today.month:02d}")
        period_index = 0 if today.day <= 14 else 1
        self.assertEqual(data["periods"][period_index]["employees"][0]["id"], self.worker.id)
        self.assertEqual(data["periods"][1 - period_index]["employees"], [])
        self.assertEqual(data["total_hours"], "8.00")
        self.assertEqual(data["total_money"], "80.00")
