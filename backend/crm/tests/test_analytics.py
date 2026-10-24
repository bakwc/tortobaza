from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from crm.analytics import clients, production, pulse, weight_kg, windows
from crm.models import CrmOrder

_UTC = ZoneInfo("UTC")


def _order(**kwargs) -> CrmOrder:
    fields = {
        "date": date(2026, 10, 10),
        "contact": "Customer",
        "weight": "1 кг",
        "filling": "Vanilla",
        "cake_price": Decimal("10.00"),
    }
    fields.update(kwargs)
    return CrmOrder.objects.create(**fields)


class WeightTests(SimpleTestCase):
    def test_known_forms(self):
        self.assertEqual(weight_kg("600"), Decimal("0.6"))
        self.assertEqual(weight_kg("1,5 кг"), Decimal("1.5"))
        self.assertEqual(weight_kg("1000 грамм"), Decimal("1"))
        self.assertEqual(weight_kg("2 kg"), Decimal("2"))
        self.assertEqual(weight_kg("600 gramm"), Decimal("0.6"))
        self.assertEqual(weight_kg("1 кг, 600"), Decimal("1.6"))
        self.assertEqual(weight_kg("1 кг, 1 кг"), Decimal("2"))

    def test_unknown_text(self):
        self.assertIsNone(weight_kg(""))
        self.assertIsNone(weight_kg("—"))
        self.assertIsNone(weight_kg("Банкейки"))
        self.assertIsNone(weight_kg("4 шт"))


class WindowTests(SimpleTestCase):
    def test_partial_month_matches_previous_day(self):
        start, end, prev_start, prev_end = windows("2026-10", date(2026, 10, 25))
        self.assertEqual((start, end), (date(2026, 10, 1), date(2026, 10, 25)))
        self.assertEqual((prev_start, prev_end), (date(2026, 9, 1), date(2026, 9, 25)))

    def test_closed_month_uses_full_previous(self):
        start, end, prev_start, prev_end = windows("2026-09", date(2026, 10, 25))
        self.assertEqual((start, end), (date(2026, 9, 1), date(2026, 9, 30)))
        self.assertEqual((prev_start, prev_end), (date(2026, 8, 1), date(2026, 8, 31)))

    def test_march_partial_clips_february(self):
        _start, end, prev_start, prev_end = windows("2026-03", date(2026, 3, 30))
        self.assertEqual(end, date(2026, 3, 30))
        self.assertEqual((prev_start, prev_end), (date(2026, 2, 1), date(2026, 2, 28)))


class AnalyticsPulseTests(TestCase):
    def test_equal_window_skips_deleted_and_outside_days(self):
        _order(date=date(2026, 10, 10), cake_price=Decimal("10.00"), delivery_price=Decimal("2.00"), weight="600")
        _order(date=date(2026, 10, 12), cake_price=Decimal("0.00"), weight="")
        _order(date=date(2026, 10, 26), cake_price=Decimal("99.00"))
        _order(date=date(2026, 9, 10), cake_price=Decimal("5.00"), weight="1 кг")
        _order(date=date(2026, 9, 26), cake_price=Decimal("99.00"))
        _order(date=date(2026, 10, 11), cake_price=Decimal("50.00"), deleted=True)
        report = pulse("2026-10", date(2026, 10, 25))
        self.assertEqual(report["current"]["orders"], 2)
        self.assertEqual(report["current"]["revenue"], "12.00")
        self.assertEqual(report["current"]["average_check"], "6.00")
        self.assertEqual(report["current"]["kilograms"], "0.6")
        self.assertEqual(report["current"]["weight_unknown"], 1)
        self.assertEqual(report["previous"]["orders"], 1)
        self.assertEqual(report["previous"]["revenue"], "5.00")
        self.assertEqual(report["previous"]["kilograms"], "1")
        self.assertEqual(len(report["weekdays"]), 7)
        self.assertEqual(report["weeks"][0]["start"], "2026-10-01")


class AnalyticsLoadTests(TestCase):
    def test_slot_boundaries(self):
        _order(date=date(2026, 10, 1), time_start=time(13, 0))
        _order(date=date(2026, 10, 1), time_start=time(14, 0))
        _order(date=date(2026, 10, 1), time_start=time(0, 0))
        _order(date=date(2026, 10, 2), time_start=time(18, 0), time_end=time(19, 0))
        _order(date=date(2026, 10, 2), time_start=None)
        report = production("2026-10", date(2026, 10, 25))
        slots = report["slots"]
        self.assertEqual(slots["morning"], 2)
        self.assertEqual(slots["day"], 1)
        self.assertEqual(slots["evening"], 1)
        self.assertEqual(slots["exact"], 3)
        self.assertEqual(slots["interval"], 1)
        self.assertEqual(slots["missing"], 1)
        self.assertEqual(slots["hours"][0]["orders"], 1)
        self.assertEqual(slots["hours"][13]["orders"], 1)
        self.assertEqual(slots["hours"][18]["orders"], 1)

    def test_lead_uses_tbilisi_date(self):
        same_day = _order(date=date(2026, 9, 4), contact="555111111")
        next_day = _order(date=date(2026, 9, 6), contact="555222222")
        CrmOrder.objects.filter(pk=same_day.pk).update(
            created_at=datetime(2026, 9, 4, 10, 0, tzinfo=_UTC)
        )
        CrmOrder.objects.filter(pk=next_day.pk).update(
            created_at=datetime(2026, 9, 4, 20, 1, tzinfo=_UTC)
        )
        report = production("2026-09", date(2026, 10, 25))
        self.assertEqual(report["lead"]["same_day"], 1)
        self.assertEqual(report["lead"]["next_day"], 1)
        self.assertEqual(report["lead"]["median"], "0.5")
        self.assertEqual(report["horizon"]["tomorrow"]["date"], "2026-10-26")
        self.assertEqual(report["horizon"]["day_after"]["date"], "2026-10-27")


class AnalyticsClientTests(TestCase):
    def test_phones_names_and_lapsed(self):
        _order(date=date(2026, 6, 1), contact="Екатерина Иванова 555111111", cake_price=Decimal("100.00"), delivery_price=Decimal("5.00"))
        _order(date=date(2026, 7, 1), contact="Екатерина Иванова 555222222", cake_price=Decimal("50.00"))
        _order(date=date(2026, 8, 1), contact="Анна", nickname="555333333", cake_price=Decimal("10.00"))
        _order(date=date(2026, 8, 2), contact="+995555333333", cake_price=Decimal("10.00"))
        _order(date=date(2026, 5, 1), contact="сайт 555444444", cake_price=Decimal("7.00"))
        _order(date=date(2026, 5, 2), contact="сайт 555555555", cake_price=Decimal("8.00"))
        _order(date=date(2026, 5, 3), contact="флао", cake_price=Decimal("9.00"))
        _order(date=date(2026, 5, 4), contact="Мария Петровна Длинная", cake_price=Decimal("9.00"))
        _order(date=date(2026, 1, 1), contact="555666666", cake_price=Decimal("200.00"))
        _order(date=date(2026, 2, 1), contact="555777777", cake_price=Decimal("80.00"))
        _order(date=date(2026, 10, 1), contact="555888888", cake_price=Decimal("30.00"))
        report = clients(date(2026, 10, 25))
        self.assertEqual(report["unknown_orders"], 2)
        self.assertEqual(report["clients"], 7)
        self.assertEqual(report["repeat_clients"], 2)
        self.assertEqual(report["frequency"]["once"]["clients"], 5)
        self.assertEqual(report["frequency"]["twice"]["clients"], 2)
        self.assertEqual(report["frequency"]["more"]["clients"], 0)
        named = [row for row in report["top_orders"] if set(row["phones"]) == {"555111111", "555222222"}]
        self.assertEqual(len(named), 1)
        self.assertEqual(named[0]["orders"], 2)
        self.assertEqual(named[0]["revenue"], "155.00")
        phoned = [row for row in report["top_orders"] if row["phones"] == ["555333333"]]
        self.assertEqual(phoned[0]["orders"], 2)
        self.assertEqual([row["revenue"] for row in report["lapsed"]], ["200.00", "80.00"])
        june = next(row for row in report["months"] if row["month"] == "2026-06")
        july = next(row for row in report["months"] if row["month"] == "2026-07")
        self.assertEqual(june["new_orders"], 1)
        self.assertEqual(july["return_orders"], 1)
        self.assertEqual(july["return_revenue"], "50.00")


class AnalyticsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.worker = User.objects.create_user(username="worker", password="password")
        self.staff = User.objects.create_user(username="staff", password="password", is_staff=True)
        self.finance = User.objects.create_user(username="finance", password="password")
        UserProfile.objects.create(user=self.finance, is_finance_admin=True)

    def test_unauthenticated_access_denied(self):
        response = self.client.get("/api/crm/analytics/pulse/")
        self.assertEqual(response.status_code, 403)

    def test_worker_access_denied(self):
        self.client.force_authenticate(user=self.worker)
        response = self.client.get("/api/crm/analytics/load/")
        self.assertEqual(response.status_code, 403)

    def test_staff_can_read(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/api/crm/analytics/pulse/", {"month": "2026-10"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["month"], "2026-10")

    def test_finance_admin_can_read(self):
        self.client.force_authenticate(user=self.finance)
        response = self.client.get("/api/crm/analytics/clients/")
        self.assertEqual(response.status_code, 200)
