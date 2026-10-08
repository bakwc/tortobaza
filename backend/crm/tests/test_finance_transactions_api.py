import uuid
from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import serializers
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
        inside.refresh_from_db()
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
                        "account": {
                            "id": self.account.pk,
                            "name": "Liberty",
                            "kind": "bank",
                            "bank_name": "",
                            "iban": "",
                            "currency": "GEL",
                        },
                        "counterparty_name": "Client",
                        "counterparty_iban": "",
                        "description": "Cake",
                        "external_id": "",
                        "transfer_id": None,
                        "flowwow_order_number": None,
                        "crm_orders": [],
                        "matched_account": None,
                        "matched_transaction": None,
                        "created_at": serializers.DateTimeField().to_representation(inside.created_at),
                        "updated_at": serializers.DateTimeField().to_representation(inside.updated_at),
                    }
                ],
            },
        )

    def test_detail_fields(self):
        account = FinancialAccount.objects.create(
            name="TBC",
            kind=FinancialAccount.KIND_BANK,
            bank_name="TBC Bank",
            iban="GE00TB0000000000000001",
            currency="USD",
        )
        transfer_id = uuid.uuid4()
        tx = FinancialTransaction.objects.create(
            account=account,
            date=self.day,
            amount=Decimal("-15.00"),
            kind=FinancialTransaction.KIND_TRANSFER,
            counterparty_name="Supplier",
            counterparty_iban="GE00BG0000000000000002",
            description="Payment",
            external_id="ext-1",
            transfer_id=transfer_id,
        )
        other = _tx(
            self.account,
            self.day,
            Decimal("15.00"),
            FinancialTransaction.KIND_TRANSFER,
            counterparty="TBC",
            description="Incoming",
        )
        tx.matched_transaction = other
        tx.save(update_fields=["matched_transaction"])
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/finance/transactions/", {"date": "2026-06-15"})
        self.assertEqual(response.status_code, 200)
        row = {row["id"]: row for row in response.json()["transactions"]}[tx.pk]
        self.assertEqual(
            row["account"],
            {
                "id": account.pk,
                "name": "TBC",
                "kind": "bank",
                "bank_name": "TBC Bank",
                "iban": "GE00TB0000000000000001",
                "currency": "USD",
            },
        )
        self.assertEqual(row["counterparty_iban"], "GE00BG0000000000000002")
        self.assertEqual(row["external_id"], "ext-1")
        self.assertEqual(row["transfer_id"], str(transfer_id))
        self.assertEqual(
            row["matched_transaction"],
            {
                "id": other.pk,
                "date": "2026-06-15",
                "amount": "15.00",
                "account": {"id": self.account.pk, "name": "Liberty"},
                "counterparty_name": "TBC",
                "description": "Incoming",
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

    def test_matched_transfer_returns_other_side_account(self):
        bog = FinancialAccount.objects.create(name="BOG", kind=FinancialAccount.KIND_BANK)
        outgoing = _tx(self.account, self.day, Decimal("-50.00"), FinancialTransaction.KIND_TRANSFER)
        incoming = _tx(bog, self.day, Decimal("50.00"), FinancialTransaction.KIND_TRANSFER)
        outgoing.matched_transaction = incoming
        outgoing.save(update_fields=["matched_transaction"])
        incoming.matched_transaction = outgoing
        incoming.save(update_fields=["matched_transaction"])
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/finance/transactions/", {"date": "2026-06-15"})
        self.assertEqual(response.status_code, 200)
        rows = {row["id"]: row for row in response.json()["transactions"]}
        self.assertEqual(rows[outgoing.pk]["matched_account"], {"id": bog.pk, "name": "BOG"})
        self.assertEqual(
            rows[incoming.pk]["matched_account"],
            {"id": self.account.pk, "name": "Liberty"},
        )

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
