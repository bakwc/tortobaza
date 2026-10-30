from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from attendance.models import AttendanceEvent, ScheduleDay

_TB = ZoneInfo("Asia/Tbilisi")


def _dt(day: date, hour: int, minute: int) -> datetime:
    return timezone.make_aware(datetime(day.year, day.month, day.day, hour, minute), _TB)


class ScheduleApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.worker = User.objects.create_user(username="worker", password="password")
        UserProfile.objects.create(
            user=self.worker,
            internal_name="Настя",
            position="Кондитер",
            in_schedule=True,
        )
        self.finance = User.objects.create_user(username="finance", password="password")
        UserProfile.objects.create(user=self.finance, is_finance_admin=True, internal_name="Босс")

    def test_worker_reads_schedule_and_cannot_change_it(self):
        self.client.force_authenticate(user=self.worker)
        read = self.client.get("/api/attendance/schedule/?month=2026-11")
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json()["employees"][0]["name"], "Настя")

        denied = self.client.put(
            "/api/attendance/schedule/",
            {"cells": [{"user": self.worker.id, "date": "2026-11-01", "day_type": "work"}]},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        fill = self.client.post(
            "/api/attendance/schedule/fill/",
            {
                "user": self.worker.id,
                "start": "2026-11-01",
                "end": "2026-11-02",
                "cycle_start": "2026-11-01",
                "pattern": ["work", "off"],
            },
            format="json",
        )
        self.assertEqual(fill.status_code, 403)
        timesheet = self.client.get("/api/attendance/timesheet/?month=2026-11")
        self.assertEqual(timesheet.status_code, 403)

    def test_save_and_delete_cells(self):
        self.client.force_authenticate(user=self.finance)
        saved = self.client.put(
            "/api/attendance/schedule/",
            {"cells": [{"user": self.worker.id, "date": "2026-11-01", "day_type": "work"}]},
            format="json",
        )
        self.assertEqual(saved.status_code, 204)
        self.assertTrue(
            ScheduleDay.objects.filter(
                user=self.worker,
                date=date(2026, 11, 1),
                day_type=ScheduleDay.WORK,
            ).exists()
        )
        grid = self.client.get("/api/attendance/schedule/?month=2026-11")
        self.assertEqual(grid.status_code, 200)
        body = grid.json()
        self.assertEqual(len(body["employees"]), 1)
        employee = body["employees"][0]
        self.assertEqual(employee["name"], "Настя")
        self.assertEqual(employee["position"], "Кондитер")
        self.assertEqual(employee["days"]["2026-11-01"], "work")

        deleted = self.client.put(
            "/api/attendance/schedule/",
            {"cells": [{"user": self.worker.id, "date": "2026-11-01", "day_type": None}]},
            format="json",
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(ScheduleDay.objects.filter(user=self.worker).exists())

    def test_fill_continues_cycle_from_previous_month(self):
        self.client.force_authenticate(user=self.finance)
        response = self.client.post(
            "/api/attendance/schedule/fill/",
            {
                "user": self.worker.id,
                "start": "2026-11-01",
                "end": "2026-11-06",
                "cycle_start": "2026-10-29",
                "pattern": ["work", "work", "work", "work", "off", "off"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 204)
        days = {
            row.date.isoformat(): row.day_type
            for row in ScheduleDay.objects.filter(user=self.worker).order_by("date")
        }
        self.assertEqual(
            days,
            {
                "2026-11-01": "work",
                "2026-11-02": "off",
                "2026-11-03": "off",
                "2026-11-04": "work",
                "2026-11-05": "work",
                "2026-11-06": "work",
            },
        )

    def test_timesheet_hours_and_mismatches(self):
        ScheduleDay.objects.create(user=self.worker, date=date(2026, 11, 1), day_type=ScheduleDay.WORK)
        ScheduleDay.objects.create(user=self.worker, date=date(2026, 11, 2), day_type=ScheduleDay.OFF)
        ScheduleDay.objects.create(user=self.worker, date=date(2026, 11, 3), day_type=ScheduleDay.WORK)
        ScheduleDay.objects.create(user=self.worker, date=date(2026, 11, 15), day_type=ScheduleDay.WORK)
        AttendanceEvent.objects.create(
            user=self.worker,
            event_type=AttendanceEvent.ARRIVAL,
            timestamp=_dt(date(2026, 11, 2), 9, 0),
        )
        AttendanceEvent.objects.create(
            user=self.worker,
            event_type=AttendanceEvent.DEPARTURE,
            timestamp=_dt(date(2026, 11, 2), 17, 0),
        )
        AttendanceEvent.objects.create(
            user=self.worker,
            event_type=AttendanceEvent.ARRIVAL,
            timestamp=_dt(date(2026, 11, 3), 9, 0),
        )
        AttendanceEvent.objects.create(
            user=self.worker,
            event_type=AttendanceEvent.DEPARTURE,
            timestamp=_dt(date(2026, 11, 3), 17, 0),
        )
        self.client.force_authenticate(user=self.finance)
        with patch("attendance.views.timezone.now", return_value=_dt(date(2026, 11, 10), 12, 0)):
            response = self.client.get("/api/attendance/timesheet/?month=2026-11")
        self.assertEqual(response.status_code, 200)
        employee = response.json()["employees"][0]
        self.assertEqual(employee["total_hours"], "16.00")
        self.assertEqual(employee["days"]["2026-11-01"]["hours"], "0.00")
        self.assertTrue(employee["days"]["2026-11-01"]["mismatch"])
        self.assertEqual(employee["days"]["2026-11-02"]["hours"], "8.00")
        self.assertEqual(employee["days"]["2026-11-02"]["day_type"], "off")
        self.assertTrue(employee["days"]["2026-11-02"]["mismatch"])
        self.assertEqual(employee["days"]["2026-11-03"]["hours"], "8.00")
        self.assertFalse(employee["days"]["2026-11-03"]["mismatch"])
        self.assertFalse(employee["days"]["2026-11-04"]["mismatch"])
        self.assertIsNone(employee["days"]["2026-11-04"]["day_type"])
        self.assertFalse(employee["days"]["2026-11-15"]["mismatch"])
