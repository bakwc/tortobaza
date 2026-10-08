from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from crm.flowwow_order_links import sync_flowwow_order_links
from crm.flowwow_statement import ACCOUNT_NAME
from crm.models import CrmOrder, FinancialAccount, FinancialTransaction

_ORDER_NUMBER = 26136332


def _order(**kwargs) -> CrmOrder:
    fields = {
        "date": date(2026, 10, 7),
        "contact": "Customer",
        "weight": "1kg",
        "filling": "Vanilla",
        "cake_price": Decimal("85.00"),
        "is_paid": True,
        "payment_type": CrmOrder.PAYMENT_FLOWWOW,
        "flowwow_order_id": _ORDER_NUMBER,
    }
    fields.update(kwargs)
    return CrmOrder.objects.create(**fields)


def _account(name: str = ACCOUNT_NAME) -> FinancialAccount:
    return FinancialAccount.objects.create(name=name, kind=FinancialAccount.KIND_VIRTUAL)


def _operation(
    transaction_type: str,
    amount: Decimal,
    kind: str,
    order_number: int = _ORDER_NUMBER,
    **kwargs,
) -> FinancialTransaction:
    fields = {
        "account": _account(),
        "date": date(2026, 10, 7),
        "amount": amount,
        "kind": kind,
        "counterparty_name": "Flowwow",
        "description": transaction_type,
        "external_id": f"{order_number}|{transaction_type}|2026-10-07 13:00:24|{amount}",
    }
    fields.update(kwargs)
    return FinancialTransaction.objects.create(**fields)


class SyncFlowwowOrderLinksTests(TestCase):
    def test_links_every_operation_of_the_order(self):
        order = _order()
        paid = _operation(
            "Paid by customer",
            Decimal("75.00"),
            FinancialTransaction.KIND_INCOME,
        )
        fee = _operation("Fee", Decimal("-15.00"), FinancialTransaction.KIND_EXPENSE)
        card_fee = _operation(
            "Card processing fee",
            Decimal("-0.30"),
            FinancialTransaction.KIND_EXPENSE,
        )
        second_card_fee = _operation(
            "Card processing fee",
            Decimal("-2.25"),
            FinancialTransaction.KIND_EXPENSE,
        )

        sync_flowwow_order_links()

        linked = {paid.pk, fee.pk, card_fee.pk, second_card_fee.pk}
        self.assertEqual(set(order.financial_transactions.values_list("pk", flat=True)), linked)
        self.assertEqual(FinancialTransaction.crm_orders.through.objects.count(), 4)

    def test_skips_withdrawal_unknown_order_and_ineligible_rows(self):
        order = _order()
        kept = _operation(
            "Paid by customer",
            Decimal("75.00"),
            FinancialTransaction.KIND_INCOME,
        )
        withdrawal = _operation(
            "Withdrawal",
            Decimal("-391.13"),
            FinancialTransaction.KIND_WITHDRAWAL,
            order_number=2450790,
        )
        unknown = _operation(
            "Paid by customer",
            Decimal("80.00"),
            FinancialTransaction.KIND_INCOME,
            order_number=24163721,
        )
        malformed = _operation(
            "Paid by customer",
            Decimal("70.00"),
            FinancialTransaction.KIND_INCOME,
            external_id="not-an-order|Paid by customer|2026-10-07 13:00:24|70.00",
        )
        other_account = _operation(
            "Paid by customer",
            Decimal("75.00"),
            FinancialTransaction.KIND_INCOME,
            account=_account("BOG business GEL"),
            external_id=f"{_ORDER_NUMBER}|Paid by customer|2026-10-07 13:00:24|75.00|other",
        )
        unpaid = _order(flowwow_order_id=26042621, is_paid=False)
        unpaid_tx = _operation(
            "Paid by customer",
            Decimal("75.00"),
            FinancialTransaction.KIND_INCOME,
            order_number=26042621,
        )
        deleted = _order(flowwow_order_id=26066974, deleted=True)
        deleted_tx = _operation(
            "Paid by customer",
            Decimal("140.00"),
            FinancialTransaction.KIND_INCOME,
            order_number=26066974,
        )
        other_type = _order(
            flowwow_order_id=26128282,
            payment_type=CrmOrder.PAYMENT_BOG,
        )
        other_type_tx = _operation(
            "Paid by customer",
            Decimal("75.00"),
            FinancialTransaction.KIND_INCOME,
            order_number=26128282,
        )

        sync_flowwow_order_links()

        self.assertEqual(kept.crm_orders.get().pk, order.pk)
        self.assertEqual(withdrawal.crm_orders.count(), 0)
        self.assertEqual(unknown.crm_orders.count(), 0)
        self.assertEqual(malformed.crm_orders.count(), 0)
        self.assertEqual(other_account.crm_orders.count(), 0)
        self.assertEqual(unpaid_tx.crm_orders.count(), 0)
        self.assertEqual(unpaid.financial_transactions.count(), 0)
        self.assertEqual(deleted_tx.crm_orders.count(), 0)
        self.assertEqual(deleted.financial_transactions.count(), 0)
        self.assertEqual(other_type_tx.crm_orders.count(), 0)
        self.assertEqual(other_type.financial_transactions.count(), 0)

    def test_links_a_new_operation_without_duplicating_the_existing_one(self):
        order = _order()
        existing = _operation(
            "Paid by customer",
            Decimal("75.00"),
            FinancialTransaction.KIND_INCOME,
        )
        existing.crm_orders.add(order)
        fee = _operation("Fee", Decimal("-15.00"), FinancialTransaction.KIND_EXPENSE)

        sync_flowwow_order_links()
        sync_flowwow_order_links()

        self.assertEqual(
            set(order.financial_transactions.values_list("pk", flat=True)),
            {existing.pk, fee.pk},
        )
        self.assertEqual(FinancialTransaction.crm_orders.through.objects.count(), 2)

    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_flowwow_orders")
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_crm_order_to_telegram")
    def test_command_links_flowwow_transaction(self, _telegram, _flowwow):
        order = _order(
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            delivery_address="",
        )
        paid = _operation(
            "Paid by customer",
            Decimal("75.00"),
            FinancialTransaction.KIND_INCOME,
        )

        call_command("sync_crm_orders_to_telegram")

        self.assertEqual(paid.crm_orders.get().pk, order.pk)
