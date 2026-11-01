from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from accounts.permissions import grant
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
        UserProfile.objects.create(user=self.finance, internal_name="Босс")
        grant(self.finance, "edit_schedule")
        self.employees_editor = User.objects.create_user(username="employees", password="password")
        grant(self.employees_editor, "edit_employees")
        self.schedule_reader = User.objects.create_user(username="reader", password="password")
        grant(self.schedule_reader, "view_schedule")

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

    def test_employees_edit_does_not_open_schedule(self):
        self.client.force_authenticate(user=self.employees_editor)
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

    def test_view_schedule_cannot_write_or_read_timesheet(self):
        self.client.force_authenticate(user=self.schedule_reader)
        read = self.client.get("/api/attendance/schedule/?month=2026-11")
        self.assertEqual(read.status_code, 200)
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
        self.assertIsNone(employee["days"]["2026-11-01"]["arrival"])
        self.assertIsNone(employee["days"]["2026-11-01"]["departure"])
        self.assertTrue(employee["days"]["2026-11-01"]["mismatch"])
        self.assertEqual(employee["days"]["2026-11-02"]["hours"], "8.00")
        self.assertEqual(employee["days"]["2026-11-02"]["arrival"], "09:00")
        self.assertEqual(employee["days"]["2026-11-02"]["departure"], "17:00")
        self.assertEqual(employee["days"]["2026-11-02"]["day_type"], "off")
        self.assertTrue(employee["days"]["2026-11-02"]["mismatch"])
        self.assertEqual(employee["days"]["2026-11-03"]["hours"], "8.00")
        self.assertEqual(employee["days"]["2026-11-03"]["arrival"], "09:00")
        self.assertEqual(employee["days"]["2026-11-03"]["departure"], "17:00")
        self.assertFalse(employee["days"]["2026-11-03"]["mismatch"])
        self.assertFalse(employee["days"]["2026-11-04"]["mismatch"])
        self.assertIsNone(employee["days"]["2026-11-04"]["day_type"])
        self.assertFalse(employee["days"]["2026-11-15"]["mismatch"])

    def test_today_overview(self):
        today = date(2026, 11, 2)
        tomorrow = date(2026, 11, 3)
        on_site = User.objects.create_user(username="anya", password="password")
        UserProfile.objects.create(user=on_site, internal_name="Аня", position="Кондитер", in_schedule=True)
        left = User.objects.create_user(username="borya", password="password")
        UserProfile.objects.create(user=left, internal_name="Боря", position="Кассир", in_schedule=True)
        waiting = User.objects.create_user(username="vera", password="password")
        UserProfile.objects.create(user=waiting, internal_name="Вера", position="Бариста", in_schedule=True)
        extra = User.objects.create_user(username="gleb", password="password")
        UserProfile.objects.create(user=extra, internal_name="Глеб", position="Курьер", in_schedule=True)
        ScheduleDay.objects.create(user=on_site, date=today, day_type=ScheduleDay.WORK)
        ScheduleDay.objects.create(user=on_site, date=tomorrow, day_type=ScheduleDay.WORK)
        ScheduleDay.objects.create(user=left, date=today, day_type=ScheduleDay.WORK)
        ScheduleDay.objects.create(user=waiting, date=today, day_type=ScheduleDay.WORK)
        ScheduleDay.objects.create(user=waiting, date=tomorrow, day_type=ScheduleDay.WORK)
        ScheduleDay.objects.create(user=extra, date=today, day_type=ScheduleDay.OFF)
        AttendanceEvent.objects.create(user=on_site, event_type=AttendanceEvent.ARRIVAL, timestamp=_dt(today, 9, 12))
        AttendanceEvent.objects.create(user=left, event_type=AttendanceEvent.ARRIVAL, timestamp=_dt(today, 9, 5))
        AttendanceEvent.objects.create(user=left, event_type=AttendanceEvent.DEPARTURE, timestamp=_dt(today, 17, 40))
        AttendanceEvent.objects.create(user=extra, event_type=AttendanceEvent.ARRIVAL, timestamp=_dt(today, 10, 0))
        self.client.force_authenticate(user=self.schedule_reader)
        with patch("attendance.views.timezone.now", return_value=_dt(today, 18, 0)):
            response = self.client.get("/api/attendance/today/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["today"], "2026-11-02")
        self.assertEqual(body["tomorrow"], "2026-11-03")
        self.assertEqual(
            body["today_employees"],
            [
                {
                    "id": on_site.id,
                    "name": "Аня",
                    "position": "Кондитер",
                    "scheduled": True,
                    "on_site": True,
                    "arrival": "09:12",
                    "departure": None,
                },
                {
                    "id": extra.id,
                    "name": "Глеб",
                    "position": "Курьер",
                    "scheduled": False,
                    "on_site": True,
                    "arrival": "10:00",
                    "departure": None,
                },
                {
                    "id": left.id,
                    "name": "Боря",
                    "position": "Кассир",
                    "scheduled": True,
                    "on_site": False,
                    "arrival": "09:05",
                    "departure": "17:40",
                },
                {
                    "id": waiting.id,
                    "name": "Вера",
                    "position": "Бариста",
                    "scheduled": True,
                    "on_site": False,
                    "arrival": None,
                    "departure": None,
                },
            ],
        )
        self.assertEqual(
            body["tomorrow_employees"],
            [
                {"id": on_site.id, "name": "Аня", "position": "Кондитер"},
                {"id": waiting.id, "name": "Вера", "position": "Бариста"},
            ],
        )

    def test_today_requires_view_schedule(self):
        self.client.force_authenticate(user=self.worker)
        response = self.client.get("/api/attendance/today/")
        self.assertEqual(response.status_code, 403)
