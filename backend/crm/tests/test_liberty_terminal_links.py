from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from crm.liberty_statement import TERMINAL_PREFIX
from crm.liberty_terminal_links import sync_liberty_terminal_order_links
from crm.models import CrmOrder, FinancialAccount, FinancialTransaction


def _order(**kwargs) -> CrmOrder:
    fields = {
        "date": date(2026, 8, 28),
        "contact": "Customer",
        "weight": "1kg",
        "filling": "Vanilla",
        "cake_price": Decimal("80.00"),
        "is_paid": True,
        "payment_type": CrmOrder.PAYMENT_TERMINAL,
    }
    fields.update(kwargs)
    return CrmOrder.objects.create(**fields)


def _account() -> FinancialAccount:
    return FinancialAccount.objects.create(name="Liberty", kind=FinancialAccount.KIND_BANK)


def _terminal(amount: Decimal, sales: date, tx_date: date) -> FinancialTransaction:
    return FinancialTransaction.objects.create(
        account=_account(),
        date=tx_date,
        amount=amount,
        kind=FinancialTransaction.KIND_INCOME,
        income_type=FinancialTransaction.INCOME_TERMINAL,
        description=f"{TERMINAL_PREFIX} {sales.day}.{sales.month:02d}.{sales.year}",
    )


class SyncLibertyTerminalOrderLinksTests(TestCase):
    def test_links_orders_from_slot_day_and_previous_day(self):
        orders = [
            _order(date=date(2026, 8, 27), cake_price=Decimal("95.00")),
            _order(date=date(2026, 8, 27), cake_price=Decimal("140.00")),
            _order(date=date(2026, 8, 27), cake_price=Decimal("110.00")),
            _order(date=date(2026, 8, 28), cake_price=Decimal("80.00")),
        ]
        transaction = _terminal(Decimal("413.95"), date(2026, 8, 28), date(2026, 8, 29))

        sync_liberty_terminal_order_links()

        self.assertEqual(
            set(transaction.crm_orders.values_list("pk", flat=True)),
            {order.pk for order in orders},
        )

    def test_links_single_order_at_two_percent(self):
        order = _order(date=date(2026, 8, 30), cake_price=Decimal("75.00"))
        transaction = _terminal(Decimal("73.50"), date(2026, 8, 30), date(2026, 8, 31))

        sync_liberty_terminal_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_links_single_order_at_two_point_six_percent(self):
        order = _order(date=date(2026, 9, 15), cake_price=Decimal("90.00"))
        transaction = _terminal(Decimal("87.66"), date(2026, 9, 15), date(2026, 9, 16))

        sync_liberty_terminal_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_links_mixed_rates_on_the_same_day(self):
        orders = [
            _order(date=date(2026, 9, 21), cake_price=Decimal("95.00")),
            _order(date=date(2026, 9, 21), cake_price=Decimal("70.00")),
        ]
        transaction = _terminal(Decimal("161.28"), date(2026, 9, 21), date(2026, 9, 22))

        sync_liberty_terminal_order_links()

        self.assertEqual(
            set(transaction.crm_orders.values_list("pk", flat=True)),
            {order.pk for order in orders},
        )

    def test_links_order_dated_the_day_before_sales(self):
        order = _order(date=date(2026, 9, 17), cake_price=Decimal("80.00"))
        transaction = _terminal(Decimal("77.92"), date(2026, 9, 18), date(2026, 9, 19))

        sync_liberty_terminal_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_uses_description_date_when_settlement_is_not_the_next_day(self):
        order = _order(date=date(2026, 6, 11), cake_price=Decimal("10.00"))
        transaction = FinancialTransaction.objects.create(
            account=_account(),
            date=date(2026, 6, 15),
            amount=Decimal("9.80"),
            kind=FinancialTransaction.KIND_INCOME,
            income_type=FinancialTransaction.INCOME_TERMINAL,
            description=f"{TERMINAL_PREFIX}11.06.2026",
        )

        sync_liberty_terminal_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_links_uneven_commission(self):
        order = _order(date=date(2026, 9, 2), cake_price=Decimal("85.00"))
        transaction = _terminal(Decimal("83.55"), date(2026, 9, 2), date(2026, 9, 3))

        sync_liberty_terminal_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_does_not_steal_previous_day_settlement(self):
        august_30 = _order(date=date(2026, 8, 30), cake_price=Decimal("75.00"))
        august_31 = _order(date=date(2026, 8, 31), cake_price=Decimal("100.00"))
        tx_30 = _terminal(Decimal("73.50"), date(2026, 8, 30), date(2026, 8, 31))
        tx_31 = _terminal(Decimal("98.00"), date(2026, 8, 31), date(2026, 9, 1))

        sync_liberty_terminal_order_links()

        self.assertEqual(tx_30.crm_orders.get().pk, august_30.pk)
        self.assertEqual(tx_31.crm_orders.get().pk, august_31.pk)

    def test_skips_when_two_subsets_match(self):
        _order(date=date(2026, 9, 6), cake_price=Decimal("100.00"))
        _order(date=date(2026, 9, 6), cake_price=Decimal("105.00"))
        transaction = _terminal(Decimal("95.00"), date(2026, 9, 6), date(2026, 9, 7))

        sync_liberty_terminal_order_links()

        self.assertEqual(transaction.crm_orders.count(), 0)

    def test_skips_when_commission_is_above_ten_percent(self):
        _order(date=date(2026, 9, 6), cake_price=Decimal("100.00"))
        transaction = _terminal(Decimal("89.00"), date(2026, 9, 6), date(2026, 9, 7))

        sync_liberty_terminal_order_links()

        self.assertEqual(transaction.crm_orders.count(), 0)

    def test_skips_ineligible_orders_and_transactions(self):
        kept = _order(date=date(2026, 9, 6), cake_price=Decimal("130.00"))
        kept_tx = _terminal(Decimal("127.40"), date(2026, 9, 6), date(2026, 9, 7))

        _order(date=date(2026, 9, 15), cake_price=Decimal("90.00"), is_paid=False)
        unpaid_tx = _terminal(Decimal("87.66"), date(2026, 9, 15), date(2026, 9, 16))

        _order(date=date(2026, 9, 17), cake_price=Decimal("80.00"), deleted=True)
        deleted_tx = _terminal(Decimal("77.92"), date(2026, 9, 17), date(2026, 9, 18))

        _order(
            date=date(2026, 9, 20),
            cake_price=Decimal("185.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        other_type_tx = _terminal(Decimal("181.30"), date(2026, 9, 20), date(2026, 9, 21))

        linked_order = _order(date=date(2026, 8, 30), cake_price=Decimal("75.00"))
        existing = FinancialTransaction.objects.create(
            account=_account(),
            date=date(2026, 8, 30),
            amount=Decimal("75.00"),
            kind=FinancialTransaction.KIND_INCOME,
            income_type=FinancialTransaction.INCOME_CASH,
        )
        existing.crm_orders.add(linked_order)
        linked_order_tx = _terminal(Decimal("73.50"), date(2026, 8, 30), date(2026, 8, 31))

        prelinked_order = _order(date=date(2026, 8, 28), cake_price=Decimal("80.00"))
        _order(date=date(2026, 8, 27), cake_price=Decimal("80.00"))
        prelinked_tx = _terminal(Decimal("77.92"), date(2026, 8, 28), date(2026, 8, 29))
        prelinked_tx.crm_orders.add(prelinked_order)

        online_order = _order(date=date(2026, 9, 8), cake_price=Decimal("100.00"))
        online_tx = FinancialTransaction.objects.create(
            account=_account(),
            date=date(2026, 9, 9),
            amount=Decimal("98.00"),
            kind=FinancialTransaction.KIND_INCOME,
            income_type=FinancialTransaction.INCOME_ONLINE,
            description="Reimbursement/ ORDERID 1",
        )

        sync_liberty_terminal_order_links()

        self.assertEqual(kept_tx.crm_orders.get().pk, kept.pk)
        self.assertEqual(unpaid_tx.crm_orders.count(), 0)
        self.assertEqual(deleted_tx.crm_orders.count(), 0)
        self.assertEqual(other_type_tx.crm_orders.count(), 0)
        self.assertEqual(linked_order_tx.crm_orders.count(), 0)
        self.assertEqual(prelinked_tx.crm_orders.get().pk, prelinked_order.pk)
        self.assertEqual(online_tx.crm_orders.count(), 0)
        self.assertEqual(online_order.financial_transactions.count(), 0)

    def test_second_run_does_not_duplicate_links(self):
        order = _order(date=date(2026, 8, 30), cake_price=Decimal("75.00"))
        transaction = _terminal(Decimal("73.50"), date(2026, 8, 30), date(2026, 8, 31))

        sync_liberty_terminal_order_links()
        sync_liberty_terminal_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)
        self.assertEqual(FinancialTransaction.crm_orders.through.objects.count(), 1)

    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_flowwow_orders")
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_crm_order_to_telegram")
    def test_command_links_terminal_transaction(self, _telegram, _flowwow):
        order = _order(
            date=date(2026, 10, 8),
            cake_price=Decimal("75.00"),
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            delivery_address="",
        )
        transaction = _terminal(Decimal("73.50"), date(2026, 10, 8), date(2026, 10, 9))

        call_command("sync_crm_orders_to_telegram")

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)
