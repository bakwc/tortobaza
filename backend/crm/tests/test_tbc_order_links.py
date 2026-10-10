from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.test import TestCase

from crm.models import CrmOrder, FinancialAccount, FinancialTransaction
from crm.tbc_order_links import sync_tbc_order_links
from crm.tbc_statement import BANK_NAME

_TB = ZoneInfo("Asia/Tbilisi")
_ACCOUNT_IBAN = "GE07TB7154245068100036"
_SENDER_IBAN = "GE29TB7649345064300130"
_OTHER_IBAN = "GE61TB7869945063400004"


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
        "payment_type": CrmOrder.PAYMENT_TBC,
    }
    fields.update(kwargs)
    return CrmOrder.objects.create(**fields)


def _created(order: CrmOrder, day: date) -> None:
    CrmOrder.objects.filter(pk=order.pk).update(created_at=_at(day))


def _account(**kwargs) -> FinancialAccount:
    fields = {
        "name": "TBC Daria",
        "kind": FinancialAccount.KIND_BANK,
        "bank_name": BANK_NAME,
        "iban": _ACCOUNT_IBAN,
        "currency": "GEL",
    }
    fields.update(kwargs)
    return FinancialAccount.objects.create(**fields)


def _income(
    account: FinancialAccount,
    amount: Decimal,
    tx_date: date,
    **kwargs,
) -> FinancialTransaction:
    fields = {
        "account": account,
        "date": tx_date,
        "amount": amount,
        "kind": FinancialTransaction.KIND_INCOME,
        "income_type": FinancialTransaction.INCOME_TRANSFER,
        "counterparty_iban": _SENDER_IBAN,
    }
    fields.update(kwargs)
    return FinancialTransaction.objects.create(**fields)


class SyncTbcOrderLinksTests(TestCase):
    def test_links_same_day_amount(self):
        account = _account()
        order = _order(date=date(2026, 9, 4), cake_price=Decimal("85.00"))
        transaction = _income(account, Decimal("85.00"), date(2026, 9, 4))

        sync_tbc_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_links_two_days_before_delivery(self):
        account = _account()
        order = _order(date=date(2026, 9, 10), cake_price=Decimal("110.00"))
        transaction = _income(account, Decimal("110.00"), date(2026, 9, 8))

        sync_tbc_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_created_date_links_when_delivery_is_outside_window(self):
        account = _account()
        order = _order(date=date(2026, 10, 2), cake_price=Decimal("85.00"))
        _created(order, date(2026, 9, 28))
        transaction = _income(account, Decimal("85.00"), date(2026, 9, 28))

        sync_tbc_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_three_days_outside_stays_unlinked(self):
        account = _account()
        order = _order(date=date(2026, 9, 15), cake_price=Decimal("95.00"))
        transaction = _income(account, Decimal("95.00"), date(2026, 9, 18))

        sync_tbc_order_links()

        self.assertEqual(transaction.crm_orders.count(), 0)
        self.assertEqual(order.financial_transactions.count(), 0)

    def test_equal_distance_takes_smaller_order_pk(self):
        account = _account()
        first = _order(date=date(2026, 9, 4), cake_price=Decimal("70.00"))
        second = _order(date=date(2026, 9, 4), cake_price=Decimal("70.00"))
        earlier = _income(account, Decimal("70.00"), date(2026, 9, 4))
        later = _income(account, Decimal("70.00"), date(2026, 9, 4))

        sync_tbc_order_links()

        self.assertLess(first.pk, second.pk)
        self.assertLess(earlier.pk, later.pk)
        self.assertEqual(earlier.crm_orders.get().pk, first.pk)
        self.assertEqual(later.crm_orders.count(), 0)
        self.assertEqual(second.financial_transactions.count(), 0)

    def test_same_sender_partials_link_to_sum(self):
        account = _account()
        order = _order(date=date(2026, 9, 19), cake_price=Decimal("120.00"))
        first = _income(account, Decimal("110.00"), date(2026, 9, 18))
        second = _income(account, Decimal("10.00"), date(2026, 9, 19))

        sync_tbc_order_links()

        self.assertEqual(
            set(order.financial_transactions.values_list("pk", flat=True)),
            {first.pk, second.pk},
        )

    def test_partials_use_created_date_when_delivery_is_outside_window(self):
        account = _account()
        order = _order(date=date(2026, 10, 2), cake_price=Decimal("120.00"))
        _created(order, date(2026, 9, 19))
        first = _income(account, Decimal("110.00"), date(2026, 9, 18))
        second = _income(account, Decimal("10.00"), date(2026, 9, 19))

        sync_tbc_order_links()

        self.assertEqual(
            set(order.financial_transactions.values_list("pk", flat=True)),
            {first.pk, second.pk},
        )

    def test_exact_match_leaves_topup_unlinked(self):
        account = _account()
        order = _order(date=date(2026, 9, 29), cake_price=Decimal("180.00"))
        exact = _income(account, Decimal("180.00"), date(2026, 9, 29))
        topup = _income(account, Decimal("10.00"), date(2026, 9, 30))

        sync_tbc_order_links()

        self.assertEqual(exact.crm_orders.get().pk, order.pk)
        self.assertEqual(topup.crm_orders.count(), 0)

    def test_different_senders_are_not_summed(self):
        account = _account()
        order = _order(date=date(2026, 9, 19), cake_price=Decimal("120.00"))
        first = _income(
            account,
            Decimal("110.00"),
            date(2026, 9, 18),
            counterparty_iban=_SENDER_IBAN,
        )
        second = _income(
            account,
            Decimal("10.00"),
            date(2026, 9, 19),
            counterparty_iban=_OTHER_IBAN,
        )

        sync_tbc_order_links()

        self.assertEqual(first.crm_orders.count(), 0)
        self.assertEqual(second.crm_orders.count(), 0)
        self.assertEqual(order.financial_transactions.count(), 0)

    def test_skips_own_iban_conversion(self):
        account = _account()
        order = _order(date=date(2026, 9, 10), cake_price=Decimal("33.86"))
        transaction = _income(
            account,
            Decimal("33.86"),
            date(2026, 9, 10),
            counterparty_iban=_ACCOUNT_IBAN,
        )

        sync_tbc_order_links()

        self.assertEqual(transaction.crm_orders.count(), 0)
        self.assertEqual(order.financial_transactions.count(), 0)

    def test_skips_transfer_kind(self):
        account = _account()
        order = _order(date=date(2026, 9, 7), cake_price=Decimal("740.00"))
        transaction = _income(
            account,
            Decimal("740.00"),
            date(2026, 9, 7),
            kind=FinancialTransaction.KIND_TRANSFER,
        )

        sync_tbc_order_links()

        self.assertEqual(transaction.crm_orders.count(), 0)
        self.assertEqual(order.financial_transactions.count(), 0)

    def test_skips_other_bank_and_payment_type(self):
        account = _account()
        kept = _order(date=date(2026, 9, 7), cake_price=Decimal("75.00"))
        kept_tx = _income(account, Decimal("75.00"), date(2026, 9, 7))
        _order(
            date=date(2026, 9, 12),
            cake_price=Decimal("82.00"),
            payment_type=CrmOrder.PAYMENT_BOG,
        )
        other_type_tx = _income(account, Decimal("82.00"), date(2026, 9, 12))
        other_account = _account(
            name="BOG business GEL",
            bank_name="Bank Of Georgia",
            iban="GE94BG0000000612361573",
        )
        other_account_tx = _income(other_account, Decimal("75.00"), date(2026, 9, 7))

        sync_tbc_order_links()

        self.assertEqual(kept_tx.crm_orders.get().pk, kept.pk)
        self.assertEqual(other_type_tx.crm_orders.count(), 0)
        self.assertEqual(other_account_tx.crm_orders.count(), 0)

    def test_second_run_does_not_duplicate_links(self):
        account = _account()
        order = _order(date=date(2026, 9, 4), cake_price=Decimal("85.00"))
        transaction = _income(account, Decimal("85.00"), date(2026, 9, 4))

        sync_tbc_order_links()
        sync_tbc_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)
        self.assertEqual(FinancialTransaction.crm_orders.through.objects.count(), 1)

    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_flowwow_orders")
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_crm_order_to_telegram")
    def test_command_links_tbc_transaction(self, _telegram, _flowwow):
        account = _account()
        order = _order(
            date=date(2026, 10, 8),
            cake_price=Decimal("75.00"),
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            delivery_address="",
        )
        transaction = _income(account, Decimal("75.00"), date(2026, 10, 8))

        call_command("sync_crm_orders_to_telegram")

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)
