from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from crm.cash_transactions import sync_cash_paid_order_transactions
from crm.models import CrmOrder, CrmOrderEvent, FinancialAccount, FinancialTransaction


def _order(**kwargs) -> CrmOrder:
    fields = {
        "date": date(2026, 3, 15),
        "contact": "Customer",
        "weight": "1kg",
        "filling": "Vanilla",
        "cake_price": Decimal("120.00"),
        "is_paid": True,
        "payment_type": CrmOrder.PAYMENT_CASH,
    }
    fields.update(kwargs)
    return CrmOrder.objects.create(**fields)


def _cash_account(name: str) -> FinancialAccount:
    return FinancialAccount.objects.create(name=name, kind=FinancialAccount.KIND_CASH)


def _paid_event(order: CrmOrder, created_at: datetime) -> CrmOrderEvent:
    return CrmOrderEvent.objects.create(
        order=order,
        created_at=created_at,
        action=CrmOrderEvent.ACTION_UPDATED,
        source=CrmOrderEvent.SOURCE_CRM,
        changes={"is_paid": {"old": False, "new": True}},
    )


class SyncCashPaidOrderTransactionsTests(TestCase):
    def test_uses_latest_paid_event_date_in_tbilisi(self):
        account = _cash_account("Cash")
        order = _order()
        _paid_event(order, datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc))
        _paid_event(order, datetime(2026, 10, 7, 22, 0, tzinfo=timezone.utc))

        sync_cash_paid_order_transactions()

        transaction = FinancialTransaction.objects.get()
        self.assertEqual(transaction.account_id, account.pk)
        self.assertEqual(transaction.date, date(2026, 10, 8))
        self.assertEqual(transaction.amount, Decimal("120.00"))
        self.assertEqual(transaction.kind, FinancialTransaction.KIND_INCOME)
        self.assertEqual(transaction.income_type, FinancialTransaction.INCOME_CASH)
        self.assertEqual(transaction.crm_order_id, order.pk)

        sync_cash_paid_order_transactions()
        self.assertEqual(FinancialTransaction.objects.count(), 1)

    def test_without_paid_event_uses_order_slot_date(self):
        _cash_account("Cash")
        order = _order()
        order.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        order.save(update_fields=["created_at"])
        CrmOrderEvent.objects.create(
            order=order,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            action=CrmOrderEvent.ACTION_CREATED,
            source=CrmOrderEvent.SOURCE_CRM,
            changes={"is_paid": {"old": None, "new": True}},
        )

        sync_cash_paid_order_transactions()

        self.assertEqual(FinancialTransaction.objects.get().date, date(2026, 3, 15))

    def test_skips_order_that_already_has_transaction(self):
        account = _cash_account("Cash")
        order = _order()
        FinancialTransaction.objects.create(
            account=account,
            date=date(2026, 1, 2),
            amount=Decimal("1.00"),
            kind=FinancialTransaction.KIND_EXPENSE,
            crm_order=order,
        )

        sync_cash_paid_order_transactions()

        self.assertEqual(FinancialTransaction.objects.count(), 1)

    def test_skips_unpaid_non_cash_and_deleted(self):
        _cash_account("Cash")
        _order(is_paid=False)
        _order(payment_type=CrmOrder.PAYMENT_TERMINAL)
        _order(deleted=True)
        kept = _order(cake_price=Decimal("40.00"))

        sync_cash_paid_order_transactions()

        transaction = FinancialTransaction.objects.get()
        self.assertEqual(transaction.crm_order_id, kept.pk)
        self.assertEqual(transaction.amount, Decimal("40.00"))

    def test_uses_first_cash_account(self):
        FinancialAccount.objects.create(name="Bank", kind=FinancialAccount.KIND_BANK)
        first = _cash_account("Cash A")
        _cash_account("Cash B")
        _order()

        sync_cash_paid_order_transactions()

        self.assertEqual(FinancialTransaction.objects.get().account_id, first.pk)

    def test_raises_when_cash_account_missing(self):
        _order()

        with self.assertRaises(FinancialAccount.DoesNotExist):
            sync_cash_paid_order_transactions()

        self.assertEqual(FinancialTransaction.objects.count(), 0)

    def test_does_nothing_when_there_are_no_orders(self):
        sync_cash_paid_order_transactions()
        self.assertEqual(FinancialTransaction.objects.count(), 0)

    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_flowwow_orders")
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_crm_order_to_telegram")
    def test_command_creates_cash_transaction(self, _telegram, _flowwow):
        _cash_account("Cash")
        order = _order(
            date=date(2026, 10, 8),
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            delivery_address="",
        )

        call_command("sync_crm_orders_to_telegram")

        self.assertEqual(FinancialTransaction.objects.get().crm_order_id, order.pk)
