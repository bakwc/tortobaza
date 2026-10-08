from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from crm.models import CrmOrder, FinancialAccount, FinancialTransaction

_TB = ZoneInfo("Asia/Tbilisi")


def _tx(
    account: FinancialAccount,
    day: date,
    amount: Decimal,
    kind: str,
    income_type: str = "",
    expense_type: str = "",
    counterparty: str = "",
    description: str = "",
) -> FinancialTransaction:
    return FinancialTransaction.objects.create(
        account=account,
        date=day,
        amount=amount,
        kind=kind,
        income_type=income_type,
        expense_type=expense_type,
        counterparty_name=counterparty,
        description=description,
    )


class FinanceTransactionsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.worker = User.objects.create_user(username="worker", password="password")
        self.admin = User.objects.create_user(username="admin", password="password", is_staff=True)
        self.account = FinancialAccount.objects.create(name="Liberty", kind=FinancialAccount.KIND_BANK)
        self.day = date(2026, 6, 15)

    def test_unauthenticated_access_denied(self):
        response = self.client.get("/api/crm/finance/transactions/")
        self.assertEqual(response.status_code, 403)

    def test_non_staff_access_denied(self):
        self.client.force_authenticate(user=self.worker)
        response = self.client.get("/api/crm/finance/transactions/")
        self.assertEqual(response.status_code, 403)

    def test_day_filter(self):
        inside = _tx(
            self.account,
            self.day,
            Decimal("120.50"),
            FinancialTransaction.KIND_INCOME,
            income_type=FinancialTransaction.INCOME_ONLINE,
            counterparty="Client",
            description="Cake",
        )
        _tx(self.account, date(2026, 6, 16), Decimal("10.00"), FinancialTransaction.KIND_EXPENSE)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/finance/transactions/", {"date": "2026-06-15"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "date": "2026-06-15",
                "month": None,
                "transactions": [
                    {
                        "id": inside.pk,
                        "date": "2026-06-15",
                        "amount": "120.50",
                        "kind": "income",
                        "income_type": "online",
                        "expense_type": "",
                        "account": {"id": self.account.pk, "name": "Liberty"},
                        "counterparty_name": "Client",
                        "description": "Cake",
                        "flowwow_order_number": None,
                        "crm_orders": [],
                    }
                ],
            },
        )

    def test_month_filter(self):
        june = _tx(
            self.account,
            self.day,
            Decimal("-40.00"),
            FinancialTransaction.KIND_EXPENSE,
        )
        _tx(self.account, date(2026, 7, 1), Decimal("5.00"), FinancialTransaction.KIND_INCOME)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/finance/transactions/", {"month": "2026-06"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data["date"])
        self.assertEqual(data["month"], "2026-06")
        self.assertEqual([row["id"] for row in data["transactions"]], [june.pk])
        self.assertEqual(data["transactions"][0]["amount"], "-40.00")
        self.assertEqual(data["transactions"][0]["kind"], "expense")
        self.assertEqual(data["transactions"][0]["account"]["name"], "Liberty")
        self.assertIsNone(data["transactions"][0]["flowwow_order_number"])
        self.assertEqual(data["transactions"][0]["crm_orders"], [])

    def test_flowwow_order_number_and_linked_crm_order(self):
        flowwow = FinancialAccount.objects.create(name="Flowwow", kind=FinancialAccount.KIND_VIRTUAL)
        order = CrmOrder.objects.create(
            date=date(2026, 10, 7),
            contact="Customer",
            weight="1kg",
            filling="Vanilla",
            cake_price=Decimal("85.00"),
        )
        linked = FinancialTransaction.objects.create(
            account=flowwow,
            date=self.day,
            amount=Decimal("75.00"),
            kind=FinancialTransaction.KIND_INCOME,
            counterparty_name="Flowwow",
            description="Paid by customer",
            external_id="26136332|Paid by customer|2026-06-15 13:00:24|75.00",
        )
        linked.crm_orders.add(order)
        other_account = FinancialTransaction.objects.create(
            account=self.account,
            date=self.day,
            amount=Decimal("10.00"),
            kind=FinancialTransaction.KIND_INCOME,
            external_id="26136332|Paid by customer|2026-06-15 13:00:24|10.00",
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/finance/transactions/", {"date": "2026-06-15"})
        self.assertEqual(response.status_code, 200)
        rows = {row["id"]: row for row in response.json()["transactions"]}
        self.assertEqual(rows[linked.pk]["flowwow_order_number"], 26136332)
        self.assertEqual(
            rows[linked.pk]["crm_orders"],
            [
                {
                    "id": order.pk,
                    "date": "2026-10-07",
                    "contact": "Customer",
                    "weight": "1kg",
                    "filling": "Vanilla",
                    "cake_price": "85.00",
                }
            ],
        )
        self.assertIsNone(rows[other_account.pk]["flowwow_order_number"])
        self.assertEqual(rows[other_account.pk]["crm_orders"], [])

    def test_default_today_tbilisi(self):
        today = timezone.now().astimezone(_TB).date()
        today_tx = _tx(self.account, today, Decimal("1.00"), FinancialTransaction.KIND_INCOME)
        _tx(self.account, date(2020, 1, 1), Decimal("9.00"), FinancialTransaction.KIND_INCOME)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/finance/transactions/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["date"], today.isoformat())
        self.assertIsNone(data["month"])
        self.assertEqual([row["id"] for row in data["transactions"]], [today_tx.pk])
