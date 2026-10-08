from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.test import TestCase

from crm.bog_order_links import ACCOUNT_NAME, sync_bog_order_links
from crm.models import CrmOrder, CrmOrderEvent, FinancialAccount, FinancialTransaction

_TB = ZoneInfo("Asia/Tbilisi")


def _at(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, 12, 0, tzinfo=_TB)


def _order(**kwargs) -> CrmOrder:
    fields = {
        "date": date(2026, 9, 3),
        "contact": "Customer",
        "weight": "1kg",
        "filling": "Vanilla",
        "cake_price": Decimal("80.00"),
        "is_paid": True,
        "payment_type": CrmOrder.PAYMENT_BOG,
    }
    fields.update(kwargs)
    return CrmOrder.objects.create(**fields)


def _created(order: CrmOrder, day: date) -> None:
    CrmOrder.objects.filter(pk=order.pk).update(created_at=_at(day))


def _paid(order: CrmOrder, day: date) -> None:
    CrmOrderEvent.objects.create(
        order=order,
        action=CrmOrderEvent.ACTION_UPDATED,
        source=CrmOrderEvent.SOURCE_CRM,
        changes={"is_paid": {"old": False, "new": True}},
        created_at=_at(day),
    )


def _created_paid(order: CrmOrder, day: date) -> None:
    CrmOrderEvent.objects.create(
        order=order,
        action=CrmOrderEvent.ACTION_CREATED,
        source=CrmOrderEvent.SOURCE_CRM,
        changes={"is_paid": {"old": None, "new": True}},
        created_at=_at(day),
    )


def _account(name: str) -> FinancialAccount:
    return FinancialAccount.objects.create(name=name, kind=FinancialAccount.KIND_BANK)


def _income(amount: Decimal, tx_date: date, **kwargs) -> FinancialTransaction:
    fields = {
        "account": _account(ACCOUNT_NAME),
        "date": tx_date,
        "amount": amount,
        "kind": FinancialTransaction.KIND_INCOME,
        "income_type": "",
    }
    fields.update(kwargs)
    return FinancialTransaction.objects.create(**fields)


class SyncBogOrderLinksTests(TestCase):
    def test_links_same_day_amounts(self):
        cases = [
            (date(2026, 9, 3), Decimal("270.00")),
            (date(2026, 9, 16), Decimal("125.00")),
            (date(2026, 9, 10), Decimal("65.00")),
        ]
        expected = []
        for delivery, amount in cases:
            order = _order(date=delivery, cake_price=amount)
            transaction = _income(amount, delivery)
            expected.append((transaction, order))

        sync_bog_order_links()

        for transaction, order in expected:
            self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_links_two_days_before_delivery(self):
        order = _order(date=date(2026, 9, 10), cake_price=Decimal("110.00"))
        transaction = _income(Decimal("110.00"), date(2026, 9, 8))

        sync_bog_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_links_day_before_delivery_and_history_paid_date(self):
        delivery_order = _order(date=date(2026, 9, 21), cake_price=Decimal("90.00"))
        delivery_tx = _income(Decimal("90.00"), date(2026, 9, 20))
        history_order = _order(date=date(2026, 9, 26), cake_price=Decimal("160.00"))
        _paid(history_order, date(2026, 9, 25))
        history_tx = _income(Decimal("160.00"), date(2026, 9, 25))

        sync_bog_order_links()

        self.assertEqual(delivery_tx.crm_orders.get().pk, delivery_order.pk)
        self.assertEqual(history_tx.crm_orders.get().pk, history_order.pk)

    def test_same_amount_two_days_apart_uses_delivery_when_created_paid(self):
        earlier = _order(date=date(2026, 9, 18), cake_price=Decimal("95.00"))
        later = _order(date=date(2026, 9, 20), cake_price=Decimal("95.00"))
        _created_paid(earlier, date(2026, 9, 9))
        _created_paid(later, date(2026, 9, 9))
        earlier_tx = _income(Decimal("95.00"), date(2026, 9, 18))
        later_tx = _income(Decimal("95.00"), date(2026, 9, 20))

        sync_bog_order_links()

        self.assertEqual(earlier_tx.crm_orders.get().pk, earlier.pk)
        self.assertEqual(later_tx.crm_orders.get().pk, later.pk)

    def test_links_seventy_gel_pair(self):
        august = _order(date=date(2026, 8, 29), cake_price=Decimal("70.00"))
        september = _order(date=date(2026, 9, 2), cake_price=Decimal("70.00"))
        august_tx = _income(Decimal("70.00"), date(2026, 8, 30))
        september_tx = _income(Decimal("70.00"), date(2026, 9, 1))

        sync_bog_order_links()

        self.assertEqual(august_tx.crm_orders.get().pk, august.pk)
        self.assertEqual(september_tx.crm_orders.get().pk, september.pk)

    def test_history_paid_date_beats_nearby_created_paid_delivery(self):
        history_order = _order(date=date(2026, 9, 27), cake_price=Decimal("95.00"))
        _paid(history_order, date(2026, 9, 27))
        delivery_order = _order(date=date(2026, 9, 29), cake_price=Decimal("95.00"))
        history_tx = _income(Decimal("95.00"), date(2026, 9, 27))
        delivery_tx = _income(Decimal("95.00"), date(2026, 9, 30))

        sync_bog_order_links()

        self.assertEqual(history_tx.crm_orders.get().pk, history_order.pk)
        self.assertEqual(delivery_tx.crm_orders.get().pk, delivery_order.pk)

    def test_closer_later_transaction_wins(self):
        order = _order(date=date(2026, 9, 20), cake_price=Decimal("80.00"))
        earlier = _income(Decimal("80.00"), date(2026, 9, 18))
        later = _income(Decimal("80.00"), date(2026, 9, 20))

        sync_bog_order_links()

        self.assertEqual(later.crm_orders.get().pk, order.pk)
        self.assertEqual(earlier.crm_orders.count(), 0)

    def test_three_days_outside_delivery_and_created_at_stays_unlinked(self):
        order = _order(date=date(2026, 9, 15), cake_price=Decimal("95.00"))
        _created(order, date(2026, 9, 14))
        transaction = _income(Decimal("95.00"), date(2026, 9, 18))

        sync_bog_order_links()

        self.assertEqual(transaction.crm_orders.count(), 0)
        self.assertEqual(order.financial_transactions.count(), 0)

    def test_equal_distance_to_two_orders_skips(self):
        _order(date=date(2026, 9, 18), cake_price=Decimal("95.00"))
        _order(date=date(2026, 9, 18), cake_price=Decimal("95.00"))
        transaction = _income(Decimal("95.00"), date(2026, 9, 18))

        sync_bog_order_links()

        self.assertEqual(transaction.crm_orders.count(), 0)

    def test_created_at_links_when_history_window_misses(self):
        order = _order(date=date(2026, 9, 27), cake_price=Decimal("155.00"))
        _paid(order, date(2026, 9, 27))
        _created(order, date(2026, 9, 3))
        transaction = _income(Decimal("155.00"), date(2026, 9, 3))

        sync_bog_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_payment_date_is_the_first_window(self):
        order = _order(
            date=date(2026, 9, 27),
            cake_price=Decimal("155.00"),
            payment_date=date(2026, 9, 3),
        )
        _paid(order, date(2026, 9, 27))
        paid_tx = _income(Decimal("155.00"), date(2026, 9, 3))
        delivery_tx = _income(Decimal("155.00"), date(2026, 9, 27))

        sync_bog_order_links()

        self.assertEqual(paid_tx.crm_orders.get().pk, order.pk)
        self.assertEqual(delivery_tx.crm_orders.count(), 0)

    def test_closer_center_wins(self):
        explicit = _order(
            date=date(2026, 9, 20),
            cake_price=Decimal("100.00"),
            payment_date=date(2026, 9, 3),
        )
        delivery = _order(date=date(2026, 9, 5), cake_price=Decimal("100.00"))
        transaction = _income(Decimal("100.00"), date(2026, 9, 3))

        sync_bog_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, explicit.pk)
        self.assertEqual(delivery.financial_transactions.count(), 0)

    def test_platform_payout_outside_window_does_not_take_the_order(self):
        order = _order(date=date(2026, 9, 25), cake_price=Decimal("80.00"))
        platform = _income(
            Decimal("80.00"),
            date(2026, 9, 22),
            description="gzavnilis charitskhva: IntelExpress",
        )
        payment = _income(Decimal("80.00"), date(2026, 9, 25))

        sync_bog_order_links()

        self.assertEqual(payment.crm_orders.get().pk, order.pk)
        self.assertEqual(platform.crm_orders.count(), 0)

    def test_wolt_and_udora_are_not_matched(self):
        wolt_order = _order(date=date(2026, 9, 7), cake_price=Decimal("75.00"))
        udora_order = _order(date=date(2026, 9, 10), cake_price=Decimal("65.00"))
        stonex_order = _order(date=date(2026, 9, 3), cake_price=Decimal("55.30"))
        wolt = _income(
            Decimal("75.00"),
            date(2026, 9, 7),
            counterparty_name="shps volt jorjia",
            description="Wolt payout",
        )
        udora = _income(
            Decimal("65.00"),
            date(2026, 9, 10),
            counterparty_name="UDORA PLATFORM - FZCO",
            description="RECEIVED FUNDS FROM USERS",
        )
        stonex = _income(
            Decimal("55.30"),
            date(2026, 9, 3),
            counterparty_name="Stonex Financial Limited",
            description="AGREEMENT G-1002221",
        )

        sync_bog_order_links()

        self.assertEqual(wolt.crm_orders.count(), 0)
        self.assertEqual(udora.crm_orders.count(), 0)
        self.assertEqual(stonex.crm_orders.count(), 0)
        self.assertEqual(wolt_order.financial_transactions.count(), 0)
        self.assertEqual(udora_order.financial_transactions.count(), 0)
        self.assertEqual(stonex_order.financial_transactions.count(), 0)

    def test_blank_and_transfer_income_types_link(self):
        blank_order = _order(date=date(2026, 9, 7), cake_price=Decimal("75.00"))
        transfer_order = _order(date=date(2026, 9, 10), cake_price=Decimal("65.00"))
        blank_tx = _income(Decimal("75.00"), date(2026, 9, 7), income_type="")
        transfer_tx = _income(
            Decimal("65.00"),
            date(2026, 9, 10),
            income_type=FinancialTransaction.INCOME_TRANSFER,
        )

        sync_bog_order_links()

        self.assertEqual(blank_tx.crm_orders.get().pk, blank_order.pk)
        self.assertEqual(transfer_tx.crm_orders.get().pk, transfer_order.pk)

    def test_skips_ineligible_orders_and_transactions(self):
        kept = _order(date=date(2026, 9, 7), cake_price=Decimal("75.00"))
        kept_tx = _income(Decimal("75.00"), date(2026, 9, 7))

        _order(date=date(2026, 9, 10), cake_price=Decimal("65.00"), is_paid=False)
        unpaid_tx = _income(Decimal("65.00"), date(2026, 9, 10))

        _order(date=date(2026, 9, 11), cake_price=Decimal("140.00"), deleted=True)
        deleted_tx = _income(Decimal("140.00"), date(2026, 9, 11))

        _order(
            date=date(2026, 9, 12),
            cake_price=Decimal("82.00"),
            payment_type=CrmOrder.PAYMENT_TBC,
        )
        other_type_tx = _income(Decimal("82.00"), date(2026, 9, 12))

        linked_order = _order(date=date(2026, 9, 16), cake_price=Decimal("125.00"))
        existing = _income(Decimal("125.00"), date(2026, 9, 16))
        existing.crm_orders.add(linked_order)
        linked_order_tx = _income(Decimal("125.00"), date(2026, 9, 16))

        prelinked_order = _order(date=date(2026, 9, 17), cake_price=Decimal("140.00"))
        prelinked_tx = _income(Decimal("140.00"), date(2026, 9, 17))
        prelinked_tx.crm_orders.add(prelinked_order)

        expense = FinancialTransaction.objects.create(
            account=_account(ACCOUNT_NAME),
            date=date(2026, 9, 7),
            amount=Decimal("75.00"),
            kind=FinancialTransaction.KIND_EXPENSE,
        )
        other_account_tx = _income(
            Decimal("75.00"),
            date(2026, 9, 7),
            account=_account("BOG filipp GEL"),
        )

        sync_bog_order_links()

        self.assertEqual(kept_tx.crm_orders.get().pk, kept.pk)
        self.assertEqual(unpaid_tx.crm_orders.count(), 0)
        self.assertEqual(deleted_tx.crm_orders.count(), 0)
        self.assertEqual(other_type_tx.crm_orders.count(), 0)
        self.assertEqual(linked_order_tx.crm_orders.count(), 0)
        self.assertEqual(existing.crm_orders.get().pk, linked_order.pk)
        self.assertEqual(prelinked_tx.crm_orders.get().pk, prelinked_order.pk)
        self.assertEqual(expense.crm_orders.count(), 0)
        self.assertEqual(other_account_tx.crm_orders.count(), 0)

    def test_second_run_does_not_duplicate_links(self):
        order = _order(date=date(2026, 9, 3), cake_price=Decimal("270.00"))
        transaction = _income(Decimal("270.00"), date(2026, 9, 3))

        sync_bog_order_links()
        sync_bog_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)
        self.assertEqual(FinancialTransaction.crm_orders.through.objects.count(), 1)

    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_flowwow_orders")
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_crm_order_to_telegram")
    def test_command_links_bog_transaction(self, _telegram, _flowwow):
        order = _order(
            date=date(2026, 10, 8),
            cake_price=Decimal("75.00"),
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            delivery_address="",
        )
        transaction = _income(Decimal("75.00"), date(2026, 10, 8))

        call_command("sync_crm_orders_to_telegram")

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)
