from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from attendance.models import AttendanceEvent
from attendance.salary import daily_monthly_share
from crm.analytics import clients, employees, overview, production, weight_kg, windows
from crm.models import AnalyticsOrderComposition, AnalyticsOrderCompositionItem, CrmOrder, CrmOrderEvent
from orders.models import Order

_UTC = ZoneInfo("UTC")
_TB = ZoneInfo("Asia/Tbilisi")


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


def _website_order() -> Order:
    return Order.objects.create(
        fulfillment_type=Order.FULFILLMENT_PICKUP,
        payment_method=Order.PAYMENT_CASH,
        customer_name="Site",
        customer_phone="555000000",
        customer_email="site@example.com",
    )


class AnalyticsOverviewTests(TestCase):
    def test_months_from_first_order_channels_and_payments(self):
        _order(
            date=date(2026, 7, 1),
            cake_price=Decimal("99.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
            deleted=True,
        )
        _order(
            date=date(2026, 8, 10),
            cake_price=Decimal("10.00"),
            delivery_price=Decimal("2.00"),
            weight="1 кг",
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        _order(
            date=date(2026, 10, 5),
            cake_price=Decimal("20.00"),
            weight="",
            payment_type=CrmOrder.PAYMENT_FLOWWOW,
        )
        _order(
            date=date(2026, 10, 6),
            cake_price=Decimal("8.00"),
            weight="2 кг",
            payment_type=CrmOrder.PAYMENT_CASH,
            website_order=_website_order(),
        )
        _order(
            date=date(2026, 10, 7),
            cake_price=Decimal("30.00"),
            weight="500",
            payment_type=CrmOrder.PAYMENT_TBC,
        )
        _order(
            date=date(2026, 10, 8),
            cake_price=Decimal("4.00"),
            weight="",
            payment_type=CrmOrder.PAYMENT_TERMINAL,
            flowwow_order_id=9,
            website_order=_website_order(),
        )
        report = overview(date(2026, 10, 25))
        self.assertEqual(report["first_date"], "2026-08-10")
        self.assertEqual(report["today"], "2026-10-25")
        self.assertEqual(report["current_month"], "2026-10")
        self.assertEqual(report["totals"]["orders"], 5)
        self.assertEqual(report["totals"]["revenue"], "74.00")
        self.assertEqual(report["totals"]["average_check"], "14.80")
        self.assertEqual(report["totals"]["kilograms"], "3.5")
        self.assertEqual(report["totals"]["weight_unknown"], 2)
        self.assertEqual(report["totals"]["months"], 3)
        self.assertEqual([row["month"] for row in report["months"]], ["2026-08", "2026-09", "2026-10"])
        self.assertEqual([row["partial"] for row in report["months"]], [False, False, True])
        august = report["months"][0]
        self.assertEqual(august["orders"], 1)
        self.assertEqual(august["revenue"], "12.00")
        self.assertEqual(august["average_check"], "12.00")
        self.assertEqual(august["kilograms"], "1")
        self.assertEqual(august["price_per_kg"], "12.00")
        september = report["months"][1]
        self.assertEqual(september["orders"], 0)
        self.assertEqual(september["revenue"], "0.00")
        self.assertIsNone(september["average_check"])
        self.assertIsNone(september["price_per_kg"])
        october = report["months"][2]
        self.assertEqual(october["orders"], 4)
        self.assertEqual(october["revenue"], "62.00")
        self.assertEqual(october["average_check"], "15.50")
        self.assertEqual(october["kilograms"], "2.5")
        self.assertEqual(october["weight_unknown"], 2)
        self.assertEqual(october["price_per_kg"], "15.20")
        self.assertEqual(report["channels"][0]["direct"], {"orders": 1, "revenue": "12.00"})
        self.assertEqual(report["channels"][0]["flowwow"], {"orders": 0, "revenue": "0.00"})
        self.assertEqual(report["channels"][1]["website"]["orders"], 0)
        self.assertEqual(
            report["channels"][2]["flowwow"],
            {"orders": 2, "revenue": "24.00"},
        )
        self.assertEqual(report["channels"][2]["website"], {"orders": 1, "revenue": "8.00"})
        self.assertEqual(report["channels"][2]["direct"], {"orders": 1, "revenue": "30.00"})
        self.assertEqual(
            [(row["type"], row["orders"], row["revenue"]) for row in report["payments"]],
            [
                (CrmOrder.PAYMENT_TBC, 1, "30.00"),
                (CrmOrder.PAYMENT_CASH, 2, "20.00"),
                (CrmOrder.PAYMENT_FLOWWOW, 1, "20.00"),
                (CrmOrder.PAYMENT_TERMINAL, 1, "4.00"),
            ],
        )


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
        report = clients()
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
        self.assertTrue(all(row["orders"] >= 2 for row in report["top_orders"]))
        self.assertTrue(all(row["orders"] >= 2 for row in report["top_revenue"]))
        june = next(row for row in report["months"] if row["month"] == "2026-06")
        july = next(row for row in report["months"] if row["month"] == "2026-07")
        self.assertEqual(june["new_orders"], 1)
        self.assertEqual(july["return_orders"], 1)
        self.assertEqual(july["return_revenue"], "50.00")

    def test_same_nickname_without_phone_is_one_client(self):
        _order(date=date(2026, 6, 1), contact="-", nickname="oxxrana", cake_price=Decimal("10.00"))
        _order(date=date(2026, 7, 1), contact="-", nickname="Oxxrana", cake_price=Decimal("20.00"))
        report = clients()
        self.assertEqual(report["unknown_orders"], 0)
        self.assertEqual(report["clients"], 1)
        self.assertEqual(report["repeat_clients"], 1)
        row = report["top_orders"][0]
        self.assertEqual(row["orders"], 2)
        self.assertEqual(row["phones"], [])
        self.assertEqual(row["revenue"], "30.00")

    def test_nickname_joins_single_phone(self):
        _order(date=date(2026, 6, 1), contact="555111111", nickname="jastdexter", cake_price=Decimal("10.00"))
        _order(date=date(2026, 7, 1), contact="-", nickname="jastdexter", cake_price=Decimal("15.00"))
        report = clients()
        self.assertEqual(report["unknown_orders"], 0)
        self.assertEqual(report["clients"], 1)
        row = report["top_orders"][0]
        self.assertEqual(row["orders"], 2)
        self.assertEqual(row["phones"], ["555111111"])
        self.assertEqual(row["revenue"], "25.00")

    def test_generic_and_short_nickname_stay_unknown(self):
        _order(date=date(2026, 6, 1), contact="-", nickname="Флао", cake_price=Decimal("10.00"))
        _order(date=date(2026, 6, 2), contact="-", nickname="Флао", cake_price=Decimal("10.00"))
        _order(date=date(2026, 6, 3), contact="-", nickname="Аля", cake_price=Decimal("10.00"))
        report = clients()
        self.assertEqual(report["unknown_orders"], 3)
        self.assertEqual(report["clients"], 0)

    def test_shared_nickname_does_not_merge_different_phones(self):
        _order(date=date(2026, 6, 1), contact="555111111", nickname="sofia", cake_price=Decimal("10.00"))
        _order(date=date(2026, 6, 2), contact="555222222", nickname="sofia", cake_price=Decimal("10.00"))
        _order(date=date(2026, 6, 3), contact="-", nickname="sofia", cake_price=Decimal("12.00"))
        _order(date=date(2026, 6, 4), contact="-", nickname="Sofia", cake_price=Decimal("13.00"))
        report = clients()
        self.assertEqual(report["unknown_orders"], 0)
        self.assertEqual(report["clients"], 3)
        self.assertEqual(len(report["top_orders"]), 1)
        row = report["top_orders"][0]
        self.assertEqual(row["phones"], [])
        self.assertEqual(row["orders"], 2)
        self.assertEqual(row["revenue"], "25.00")


class AnalyticsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.worker = User.objects.create_user(username="worker", password="password")
        self.staff = User.objects.create_user(username="staff", password="password", is_staff=True)
        self.finance = User.objects.create_user(username="finance", password="password")
        UserProfile.objects.create(user=self.finance, is_finance_admin=True)

    def test_unauthenticated_access_denied(self):
        response = self.client.get("/api/crm/analytics/overview/")
        self.assertEqual(response.status_code, 403)

    def test_worker_access_denied(self):
        self.client.force_authenticate(user=self.worker)
        response = self.client.get("/api/crm/analytics/load/")
        self.assertEqual(response.status_code, 403)

    def test_staff_access_denied(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/api/crm/analytics/overview/")
        self.assertEqual(response.status_code, 403)

    def test_finance_admin_can_read(self):
        self.client.force_authenticate(user=self.finance)
        response = self.client.get("/api/crm/analytics/clients/")
        self.assertEqual(response.status_code, 200)


class AnalyticsEmployeesTests(TestCase):
    def test_month_attributes_orders_and_attendance(self):
        placer = User.objects.create_user(username="anna", password="password")
        baker = User.objects.create_user(username="boris", password="password")
        courier = User.objects.create_user(username="vera", password="password")
        UserProfile.objects.create(user=baker, hourly_rate=Decimal("10.00"))
        day = date(2026, 10, 10)
        arrival = timezone.make_aware(datetime(2026, 10, 10, 9, 0), _TB)
        departure = timezone.make_aware(datetime(2026, 10, 10, 17, 0), _TB)
        AttendanceEvent.objects.create(user=baker, event_type=AttendanceEvent.ARRIVAL, timestamp=arrival)
        AttendanceEvent.objects.create(user=baker, event_type=AttendanceEvent.DEPARTURE, timestamp=departure)
        _order(
            date=day,
            created_by=placer,
            taken_by=baker,
            delivered_by=courier,
            weight="1,5 кг",
        )
        _order(
            date=date(2026, 9, 10),
            created_by=placer,
            taken_by=baker,
            delivered_by=courier,
            weight="2 кг",
        )
        _order(
            date=day,
            created_by=placer,
            taken_by=baker,
            delivered_by=courier,
            weight="3 кг",
            deleted=True,
        )
        report = employees("2026-10", date(2026, 10, 10))
        self.assertEqual(
            [
                (
                    row["name"],
                    row["made"],
                    row["made_kilograms"],
                    row["hours"],
                    row["money"],
                    row["shifts"],
                    row["arrival"],
                    row["departure"],
                )
                for row in report["employees"]
            ],
            [("boris", 1, "1.5", "8.00", "80.00", 1, "09:00", "17:00")],
        )
        self.assertEqual(report["totals"]["hours"], "8.00")
        self.assertEqual(report["totals"]["money"], "80.00")
        self.assertEqual(report["totals"]["hourly_money"], "80.00")
        self.assertEqual(report["totals"]["monthly_money"], "0.00")
        self.assertEqual(report["totals"]["kilograms"], "1.5")
        self.assertEqual(report["totals"]["revenue"], "10.00")
        self.assertEqual(report["totals"]["salary_share"], "8")
        self.assertEqual(report["totals"]["money_per_kg"], "53.33")
        self.assertEqual(report["totals"]["kg_per_hour"], "0.188")
        self.assertEqual(report["totals"]["shifts"], 1)
        self.assertEqual(report["previous"]["revenue"], "10.00")
        self.assertEqual(report["previous"]["kilograms"], "2")
        self.assertEqual(report["previous"]["money"], "0.00")
        self.assertEqual(
            [(row["month"], row["partial"], row["kilograms"], row["bakers"][0]["kilograms"]) for row in report["months"]],
            [("2026-09", False, "2", "2"), ("2026-10", True, "1.5", "1.5")],
        )
        saturday = next(row for row in report["weekdays"] if row["weekday"] == 5)
        self.assertEqual(saturday["hours"], "4.00")
        self.assertEqual(saturday["kilograms"], "0.75")
        worked = next(row for row in report["days"] if row["date"] == "2026-10-10")
        self.assertEqual(worked["kg_per_hour"], "0.188")
        self.assertEqual(worked["bakers"], [{"id": baker.id, "name": "boris", "kilograms": "1.5"}])

    def test_monthly_rate_stops_at_today(self):
        worker = User.objects.create_user(username="anna", password="password")
        UserProfile.objects.create(user=worker, monthly_rate=Decimal("310.00"))
        _order(date=date(2026, 10, 10), weight="—")
        report = employees("2026-10", date(2026, 10, 10))
        expected = sum(
            (daily_monthly_share(Decimal("310.00"), date(2026, 10, day)) for day in range(1, 11)),
            Decimal("0.00"),
        )
        self.assertEqual(report["totals"]["monthly_money"], format(expected, "f"))
        self.assertEqual(report["totals"]["monthly_money"], "100.00")
        self.assertEqual(report["employees"][0]["monthly"], True)
        self.assertEqual(report["employees"][0]["hours"], "0.00")
        self.assertIsNone(report["totals"]["money_per_kg"])

    def test_unclosed_shift_and_missing_baker(self):
        worker = User.objects.create_user(username="boris", password="password")
        UserProfile.objects.create(user=worker, hourly_rate=Decimal("10.00"))
        AttendanceEvent.objects.create(
            user=worker,
            event_type=AttendanceEvent.ARRIVAL,
            timestamp=timezone.make_aware(datetime(2026, 10, 9, 9, 0), _TB),
        )
        _order(date=date(2026, 10, 10), weight="1 кг")
        report = employees("2026-10", date(2026, 10, 10))
        self.assertEqual(report["gaps"]["without_baker"], 1)
        self.assertEqual(report["gaps"]["unclosed_shifts"], 1)
        self.assertEqual(report["days"][-1]["unassigned_kilograms"], "1")
        self.assertEqual(report["employees"][0]["hours"], "0.00")
        opened = next(day for day in report["timesheet"][0]["days"] if day["date"] == "2026-10-09")
        self.assertEqual(opened["open"], True)
        self.assertEqual(opened["hours"], "0.00")

    def test_kinds_and_production_time(self):
        baker = User.objects.create_user(username="boris", password="password")
        made = _order(date=date(2026, 10, 10), taken_by=baker, weight="1 кг")
        composition = AnalyticsOrderComposition.objects.create(
            order=made,
            source_hash="hash",
            parser=AnalyticsOrderComposition.PARSER_RULES,
        )
        AnalyticsOrderCompositionItem.objects.create(
            composition=composition,
            kind=AnalyticsOrderCompositionItem.KIND_CAKE,
            name="Cake",
            quantity=2,
        )
        AnalyticsOrderCompositionItem.objects.create(
            composition=composition,
            kind=AnalyticsOrderCompositionItem.KIND_BENTO,
            name="Bento",
            quantity=1,
        )
        CrmOrderEvent.objects.create(
            order=made,
            action=CrmOrderEvent.ACTION_UPDATED,
            source=CrmOrderEvent.SOURCE_CRM,
            created_at=timezone.make_aware(datetime(2026, 10, 10, 9, 0), _TB),
            changes={"status": {"old": "new", "new": "in_work"}},
        )
        CrmOrderEvent.objects.create(
            order=made,
            action=CrmOrderEvent.ACTION_UPDATED,
            source=CrmOrderEvent.SOURCE_CRM,
            created_at=timezone.make_aware(datetime(2026, 10, 10, 11, 0), _TB),
            changes={"status": {"old": "in_work", "new": "ready"}},
        )
        _order(date=date(2026, 10, 10), taken_by=baker, weight="1 кг")
        report = employees("2026-10", date(2026, 10, 10))
        row = report["employees"][0]
        self.assertEqual(row["made"], 2)
        self.assertEqual(row["made_kilograms"], "2")
        self.assertEqual(row["kinds"], [{"kind": "cake", "quantity": 2}, {"kind": "bento", "quantity": 1}])
        self.assertEqual(row["production_minutes"], "120")
        self.assertEqual(row["production_orders"], 1)
        self.assertEqual(report["gaps"]["without_composition"], 1)
        self.assertEqual(report["gaps"]["without_production"], 1)
