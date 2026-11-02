from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from accounts.permissions import grant
from attendance.models import AttendanceEvent, SalaryPayout
from crm.models import FinancialAccount, FinancialTransaction

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
        grant(self.admin, "view_employees")
        UserProfile.objects.create(
            user=self.worker,
            hourly_rate=Decimal("10.00"),
            internal_name="Бека",
            position="Кондитер",
        )
        UserProfile.objects.create(
            user=self.other,
            hourly_rate=Decimal("20.00"),
            internal_name="Анна",
            position="Курьер",
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
                                "full_name": "Бека",
                                "hours": "8.00",
                                "money": "80.00",
                                "position": "Кондитер",
                                "payout": None,
                            }
                        ],
                        "hourly_hours": "8.00",
                        "hourly_money": "80.00",
                        "monthly_hours": "0.00",
                        "monthly_money": "0.00",
                    },
                    {
                        "start": "2026-06-15",
                        "end": "2026-06-30",
                        "employees": [
                            {
                                "id": self.other.id,
                                "name": "Анна",
                                "full_name": "Анна",
                                "hours": "4.00",
                                "money": "80.00",
                                "position": "Курьер",
                                "payout": None,
                            },
                            {
                                "id": self.worker.id,
                                "name": "Бека",
                                "full_name": "Бека",
                                "hours": "4.00",
                                "money": "40.00",
                                "position": "Кондитер",
                                "payout": None,
                            },
                        ],
                        "hourly_hours": "8.00",
                        "hourly_money": "120.00",
                        "monthly_hours": "0.00",
                        "monthly_money": "0.00",
                    },
                ],
                "hourly_hours": "16.00",
                "hourly_money": "200.00",
                "monthly_hours": "0.00",
                "monthly_money": "0.00",
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
        self.assertEqual(data["periods"][0]["hourly_hours"], "0.00")
        self.assertEqual(data["periods"][0]["monthly_money"], "0.00")
        self.assertEqual(data["periods"][1]["end"], "2026-02-28")
        self.assertEqual(data["periods"][1]["employees"][0]["name"], "Бека")
        self.assertEqual(data["periods"][1]["employees"][0]["full_name"], "Бека")
        self.assertEqual(data["hourly_money"], "80.00")
        self.assertEqual(data["monthly_money"], "0.00")

    def test_payslip_name_uses_first_and_last_name(self):
        self.worker.first_name = "Бека"
        self.worker.last_name = "Беридзе"
        self.worker.save(update_fields=["first_name", "last_name"])
        _event(self.worker, AttendanceEvent.ARRIVAL, date(2026, 6, 10), 9, 0)
        _event(self.worker, AttendanceEvent.DEPARTURE, date(2026, 6, 10), 17, 0)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/salaries/", {"month": "2026-06"})
        self.assertEqual(response.status_code, 200)
        employee = response.json()["periods"][0]["employees"][0]
        self.assertEqual(employee["name"], "Бека")
        self.assertEqual(employee["full_name"], "Бека Беридзе")

    def test_payslip_name_uses_only_filled_part(self):
        self.worker.last_name = "Беридзе"
        self.worker.save(update_fields=["last_name"])
        _event(self.worker, AttendanceEvent.ARRIVAL, date(2026, 6, 10), 9, 0)
        _event(self.worker, AttendanceEvent.DEPARTURE, date(2026, 6, 10), 17, 0)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/salaries/", {"month": "2026-06"})
        self.assertEqual(response.status_code, 200)
        employee = response.json()["periods"][0]["employees"][0]
        self.assertEqual(employee["full_name"], "Беридзе")

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
        self.assertEqual(data["hourly_hours"], "8.00")
        self.assertEqual(data["hourly_money"], "80.00")
        self.assertEqual(data["monthly_hours"], "0.00")
        self.assertEqual(data["monthly_money"], "0.00")

    def test_detail_requires_employees_permission(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(
            f"/api/crm/salaries/{self.worker.id}/",
            {"start": "2026-06-01", "end": "2026-06-14"},
        )
        self.assertEqual(response.status_code, 403)

    def test_detail_half_month_days(self):
        _event(self.worker, AttendanceEvent.ARRIVAL, date(2026, 6, 10), 9, 0)
        _event(self.worker, AttendanceEvent.DEPARTURE, date(2026, 6, 10), 17, 0)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            f"/api/crm/salaries/{self.worker.id}/",
            {"start": "2026-06-01", "end": "2026-06-14"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Бека")
        self.assertEqual(data["position"], "Кондитер")
        self.assertEqual(data["hourly_rate"], "10.00")
        self.assertEqual(data["monthly"], False)
        self.assertEqual(len(data["rows"]), 14)
        day = next(row for row in data["rows"] if row["date"] == "2026-06-10")
        self.assertEqual(day["hours"], "8.00")
        self.assertEqual(day["money"], "80.00")
        self.assertIsNotNone(day["arrival"])
        self.assertIsNotNone(day["departure"])
        idle = next(row for row in data["rows"] if row["date"] == "2026-06-01")
        self.assertIsNone(idle["arrival"])
        self.assertIsNone(idle["departure"])
        self.assertEqual(data["total_hours"], "8.00")
        self.assertEqual(data["total_money"], "80.00")

    def test_payout_creates_salary_expense(self):
        _event(self.worker, AttendanceEvent.ARRIVAL, date(2026, 6, 10), 9, 0)
        _event(self.worker, AttendanceEvent.DEPARTURE, date(2026, 6, 10), 17, 0)
        self.worker.first_name = "Бека"
        self.worker.last_name = "Беридзе"
        self.worker.save(update_fields=["first_name", "last_name"])
        account = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        grant(self.admin, "edit_finance")
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/crm/salaries/{self.worker.id}/payout/",
            {
                "start": "2026-06-01",
                "end": "2026-06-14",
                "account_id": account.pk,
                "date": "2026-06-16",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        tx = FinancialTransaction.objects.get()
        self.assertEqual(response.json()["id"], tx.pk)
        self.assertEqual(tx.amount, Decimal("-80.00"))
        self.assertEqual(tx.kind, FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(tx.expense_type, FinancialTransaction.EXPENSE_SALARY)
        self.assertEqual(tx.income_type, "")
        self.assertEqual(tx.account_id, account.pk)
        self.assertEqual(tx.date, date(2026, 6, 16))
        self.assertEqual(tx.counterparty_name, "Бека Беридзе")
        self.assertEqual(tx.description, "2026-06-01–2026-06-14")
        payout = SalaryPayout.objects.get()
        self.assertEqual(payout.user_id, self.worker.id)
        self.assertEqual(payout.period_start, date(2026, 6, 1))
        self.assertEqual(payout.period_end, date(2026, 6, 14))
        self.assertEqual(payout.financial_transaction_id, tx.pk)
        listed = self.client.get("/api/crm/salaries/", {"month": "2026-06"})
        self.assertEqual(listed.status_code, 200)
        employee = listed.json()["periods"][0]["employees"][0]
        self.assertEqual(
            employee["payout"],
            {
                "id": tx.pk,
                "date": "2026-06-16",
                "amount": "-80.00",
                "counterparty_name": "Бека Беридзе",
            },
        )
        self.assertEqual(listed.json()["periods"][1]["employees"], [])

    def test_payout_duplicate_conflict(self):
        _event(self.worker, AttendanceEvent.ARRIVAL, date(2026, 6, 10), 9, 0)
        _event(self.worker, AttendanceEvent.DEPARTURE, date(2026, 6, 10), 17, 0)
        account = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        grant(self.admin, "edit_finance")
        self.client.force_authenticate(user=self.admin)
        body = {
            "start": "2026-06-01",
            "end": "2026-06-14",
            "account_id": account.pk,
            "date": "2026-06-16",
        }
        first = self.client.post(
            f"/api/crm/salaries/{self.worker.id}/payout/",
            body,
            format="json",
        )
        self.assertEqual(first.status_code, 201)
        second = self.client.post(
            f"/api/crm/salaries/{self.worker.id}/payout/",
            body,
            format="json",
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(FinancialTransaction.objects.count(), 1)
        self.assertEqual(SalaryPayout.objects.count(), 1)

    def test_payout_requires_edit_finance(self):
        account = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/crm/salaries/{self.worker.id}/payout/",
            {
                "start": "2026-06-01",
                "end": "2026-06-14",
                "account_id": account.pk,
                "date": "2026-06-16",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(FinancialTransaction.objects.count(), 0)

    def test_payout_rejects_empty_salary_and_bad_period(self):
        account = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        grant(self.admin, "edit_finance")
        self.client.force_authenticate(user=self.admin)
        empty = self.client.post(
            f"/api/crm/salaries/{self.worker.id}/payout/",
            {
                "start": "2026-06-01",
                "end": "2026-06-14",
                "account_id": account.pk,
                "date": "2026-06-16",
            },
            format="json",
        )
        self.assertEqual(empty.status_code, 400)
        bad_period = self.client.post(
            f"/api/crm/salaries/{self.worker.id}/payout/",
            {
                "start": "2026-06-02",
                "end": "2026-06-14",
                "account_id": account.pk,
                "date": "2026-06-16",
            },
            format="json",
        )
        self.assertEqual(bad_period.status_code, 400)
        self.assertEqual(FinancialTransaction.objects.count(), 0)
