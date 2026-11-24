from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.permissions import grant
from crm.models import CrmOrder, FinancialAccount, FinancialTransaction
from tortobaza.finance_db import use_finance_db


def _order(**kwargs) -> CrmOrder:
    fields = {
        "date": date(2026, 6, 2),
        "contact": "Recipient",
        "cake_price": Decimal("80.00"),
        "delivery_price": Decimal("10.00"),
        "prepayment": Decimal("0.00"),
        "is_paid": True,
        "payment_type": CrmOrder.PAYMENT_BOG,
        "payment_date": date(2026, 6, 1),
        "time_start": time(14, 0),
        "time_end": time(16, 0),
    }
    fields.update(kwargs)
    return CrmOrder.objects.create(**fields)


def _income(account: FinancialAccount, day: date, amount: str) -> FinancialTransaction:
    return FinancialTransaction.objects.create(
        account=account,
        date=day,
        amount=Decimal(amount),
        kind=FinancialTransaction.KIND_INCOME,
        income_type=FinancialTransaction.INCOME_TRANSFER,
    )


class FinanceOrderLinksApiTests(TestCase):
    databases = {"default", "personal"}

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username="admin", password="password")
        grant(self.admin, "view_finance", "view_order_delivery_contacts")
        self.client.force_authenticate(user=self.admin)
        self.account = FinancialAccount.objects.create(name="BOG", kind=FinancialAccount.KIND_BANK)

    def test_without_permission_is_denied(self):
        stranger = User.objects.create_user(username="stranger", password="password")
        self.client.force_authenticate(user=stranger)
        response = self.client.get("/api/crm/finance/order-links/", {"month": "2026-06", "scope": "business"})
        self.assertEqual(response.status_code, 403)

    def test_month_lists_linked_and_unlinked_and_hides_deleted(self):
        linked = _order()
        tx = _income(self.account, date(2026, 6, 1), "90.00")
        tx.crm_orders.add(linked)
        unlinked = _order(
            date=date(2026, 6, 10),
            contact="Later",
            is_paid=False,
            payment_type=CrmOrder.PAYMENT_CASH,
            payment_date=None,
            time_start=None,
            time_end=None,
            when_ready=True,
        )
        _order(date=date(2026, 6, 5), deleted=True)
        _order(date=date(2026, 5, 31))
        response = self.client.get(
            "/api/crm/finance/order-links/",
            {"month": "2026-06", "scope": "business"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "month": "2026-06",
                "orders": [
                    {
                        "id": linked.pk,
                        "date": "2026-06-02",
                        "time_start": "14:00:00",
                        "time_end": "16:00:00",
                        "when_ready": False,
                        "contact": "Recipient",
                        "cake_price": "80.00",
                        "delivery_price": "10.00",
                        "prepayment": "0.00",
                        "is_paid": True,
                        "payment_type": "bog",
                        "payment_date": "2026-06-01",
                        "transactions": [
                            {
                                "id": tx.pk,
                                "date": "2026-06-01",
                                "amount": "90.00",
                                "account_name": "BOG",
                                "income_type": "transfer",
                            }
                        ],
                    },
                    {
                        "id": unlinked.pk,
                        "date": "2026-06-10",
                        "time_start": None,
                        "time_end": None,
                        "when_ready": True,
                        "contact": "Later",
                        "cake_price": "80.00",
                        "delivery_price": "10.00",
                        "prepayment": "0.00",
                        "is_paid": False,
                        "payment_type": "cash",
                        "payment_date": None,
                        "transactions": [],
                    },
                ],
            },
        )

    def test_contact_hidden_without_permission(self):
        limited = User.objects.create_user(username="limited", password="password")
        grant(limited, "view_finance")
        _order()
        self.client.force_authenticate(user=limited)
        response = self.client.get(
            "/api/crm/finance/order-links/",
            {"month": "2026-06", "scope": "business"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["orders"][0]["contact"], "")

    def test_personal_scope_uses_personal_links(self):
        order = _order()
        business_tx = _income(self.account, date(2026, 6, 1), "90.00")
        business_tx.crm_orders.add(order)
        CrmOrder.objects.using("personal").create(
            id=order.pk,
            date=order.date,
            contact=order.contact,
            cake_price=order.cake_price,
            delivery_price=order.delivery_price,
            prepayment=order.prepayment,
            is_paid=order.is_paid,
            payment_type=order.payment_type,
            payment_date=order.payment_date,
            time_start=order.time_start,
            time_end=order.time_end,
        )
        with use_finance_db("personal"):
            personal_account = FinancialAccount.objects.create(
                name="Personal BOG",
                kind=FinancialAccount.KIND_BANK,
            )
            personal_tx = _income(personal_account, date(2026, 6, 3), "40.00")
            personal_tx.crm_orders.add(order)
        business = self.client.get(
            "/api/crm/finance/order-links/",
            {"month": "2026-06", "scope": "business"},
        )
        personal = self.client.get(
            "/api/crm/finance/order-links/",
            {"month": "2026-06", "scope": "personal"},
        )
        self.assertEqual(business.status_code, 200)
        self.assertEqual(personal.status_code, 200)
        self.assertEqual(
            [row["id"] for row in business.json()["orders"][0]["transactions"]],
            [business_tx.pk],
        )
        self.assertEqual(
            [row["account_name"] for row in personal.json()["orders"][0]["transactions"]],
            ["Personal BOG"],
        )
