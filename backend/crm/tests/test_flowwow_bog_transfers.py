from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from crm.bog_order_links import ACCOUNT_NAME as BOG_ACCOUNT_NAME
from crm.flowwow_bog_transfers import sync_flowwow_bog_transfers
from crm.flowwow_statement import ACCOUNT_NAME as FLOWWOW_ACCOUNT_NAME
from crm.models import FinancialAccount, FinancialTransaction


def _account(name: str) -> FinancialAccount:
    return FinancialAccount.objects.create(name=name, kind=FinancialAccount.KIND_BANK)


def _tx(
    account: FinancialAccount,
    day: date,
    amount: Decimal,
    kind: str,
    external_id: str,
    description: str = "",
) -> FinancialTransaction:
    return FinancialTransaction.objects.create(
        account=account,
        date=day,
        amount=amount,
        kind=kind,
        description=description,
        external_id=external_id,
    )


class SyncFlowwowBogTransfersTests(TestCase):
    def test_matches_opposite_amount_including_payment_without_agreement_marker(self):
        flowwow = _account(FLOWWOW_ACCOUNT_NAME)
        bog = _account(BOG_ACCOUNT_NAME)
        withdrawal = _tx(
            flowwow,
            date(2026, 9, 29),
            Decimal("-259.16"),
            FinancialTransaction.KIND_TRANSFER,
            "withdrawal",
        )
        income = _tx(
            bog,
            date(2026, 10, 1),
            Decimal("259.16"),
            FinancialTransaction.KIND_INCOME,
            "income",
            description=(
                "POP PAYROLLPERSONNEL PAYMENT REGIS,LUKA KORIDZE,"
                "Pay for goods and services,113520460,2133832652"
            ),
        )

        sync_flowwow_bog_transfers()

        withdrawal.refresh_from_db()
        income.refresh_from_db()
        self.assertEqual(withdrawal.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(income.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(withdrawal.matched_transaction_id, income.pk)
        self.assertEqual(income.matched_transaction_id, withdrawal.pk)
        self.assertNotIn("g-1002221", income.description.lower())

    def test_skips_amount_that_differs_by_one_tetri(self):
        flowwow = _account(FLOWWOW_ACCOUNT_NAME)
        bog = _account(BOG_ACCOUNT_NAME)
        withdrawal = _tx(
            flowwow,
            date(2026, 9, 29),
            Decimal("-259.16"),
            FinancialTransaction.KIND_TRANSFER,
            "withdrawal",
        )
        income = _tx(
            bog,
            date(2026, 10, 1),
            Decimal("259.17"),
            FinancialTransaction.KIND_INCOME,
            "income",
        )

        sync_flowwow_bog_transfers()

        withdrawal.refresh_from_db()
        income.refresh_from_db()
        self.assertEqual(withdrawal.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(income.kind, FinancialTransaction.KIND_INCOME)
        self.assertIsNone(withdrawal.matched_transaction_id)
        self.assertIsNone(income.matched_transaction_id)

    def test_matches_on_day_fourteen_and_skips_day_fifteen(self):
        flowwow = _account(FLOWWOW_ACCOUNT_NAME)
        bog = _account(BOG_ACCOUNT_NAME)
        start = date(2026, 9, 1)
        inside = _tx(
            flowwow,
            start,
            Decimal("-10.00"),
            FinancialTransaction.KIND_TRANSFER,
            "inside",
        )
        inside_income = _tx(
            bog,
            start + timedelta(days=14),
            Decimal("10.00"),
            FinancialTransaction.KIND_INCOME,
            "inside-income",
        )
        outside = _tx(
            flowwow,
            start,
            Decimal("-20.00"),
            FinancialTransaction.KIND_TRANSFER,
            "outside",
        )
        outside_income = _tx(
            bog,
            start + timedelta(days=15),
            Decimal("20.00"),
            FinancialTransaction.KIND_INCOME,
            "outside-income",
        )

        sync_flowwow_bog_transfers()

        inside.refresh_from_db()
        inside_income.refresh_from_db()
        outside.refresh_from_db()
        outside_income.refresh_from_db()
        self.assertEqual(inside.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(inside.matched_transaction_id, inside_income.pk)
        self.assertEqual(inside_income.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(inside_income.matched_transaction_id, inside.pk)
        self.assertEqual(outside.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(outside_income.kind, FinancialTransaction.KIND_INCOME)
        self.assertIsNone(outside.matched_transaction_id)
        self.assertIsNone(outside_income.matched_transaction_id)

    def test_skips_bog_income_dated_before_the_withdrawal(self):
        flowwow = _account(FLOWWOW_ACCOUNT_NAME)
        bog = _account(BOG_ACCOUNT_NAME)
        withdrawal = _tx(
            flowwow,
            date(2026, 9, 10),
            Decimal("-55.30"),
            FinancialTransaction.KIND_TRANSFER,
            "withdrawal",
        )
        income = _tx(
            bog,
            date(2026, 9, 9),
            Decimal("55.30"),
            FinancialTransaction.KIND_INCOME,
            "income",
        )

        sync_flowwow_bog_transfers()

        withdrawal.refresh_from_db()
        income.refresh_from_db()
        self.assertEqual(withdrawal.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(income.kind, FinancialTransaction.KIND_INCOME)

    def test_skips_zero_amount(self):
        flowwow = _account(FLOWWOW_ACCOUNT_NAME)
        bog = _account(BOG_ACCOUNT_NAME)
        withdrawal = _tx(
            flowwow,
            date(2026, 9, 1),
            Decimal("0.00"),
            FinancialTransaction.KIND_TRANSFER,
            "withdrawal",
        )
        income = _tx(
            bog,
            date(2026, 9, 1),
            Decimal("0.00"),
            FinancialTransaction.KIND_INCOME,
            "income",
        )

        sync_flowwow_bog_transfers()

        withdrawal.refresh_from_db()
        income.refresh_from_db()
        self.assertEqual(withdrawal.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(income.kind, FinancialTransaction.KIND_INCOME)
        self.assertIsNone(withdrawal.matched_transaction_id)
        self.assertIsNone(income.matched_transaction_id)

    def test_skips_when_two_incomes_share_the_amount(self):
        flowwow = _account(FLOWWOW_ACCOUNT_NAME)
        bog = _account(BOG_ACCOUNT_NAME)
        start = date(2026, 9, 1)
        withdrawal = _tx(
            flowwow,
            start,
            Decimal("-100.00"),
            FinancialTransaction.KIND_TRANSFER,
            "withdrawal",
        )
        first = _tx(
            bog,
            start + timedelta(days=1),
            Decimal("100.00"),
            FinancialTransaction.KIND_INCOME,
            "first",
        )
        second = _tx(
            bog,
            start + timedelta(days=2),
            Decimal("100.00"),
            FinancialTransaction.KIND_INCOME,
            "second",
        )

        sync_flowwow_bog_transfers()

        withdrawal.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(withdrawal.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(first.kind, FinancialTransaction.KIND_INCOME)
        self.assertEqual(second.kind, FinancialTransaction.KIND_INCOME)
        self.assertIsNone(withdrawal.matched_transaction_id)
        self.assertIsNone(first.matched_transaction_id)
        self.assertIsNone(second.matched_transaction_id)

    def test_second_sync_leaves_the_pair_unchanged(self):
        flowwow = _account(FLOWWOW_ACCOUNT_NAME)
        bog = _account(BOG_ACCOUNT_NAME)
        withdrawal = _tx(
            flowwow,
            date(2026, 9, 8),
            Decimal("-417.87"),
            FinancialTransaction.KIND_TRANSFER,
            "withdrawal",
        )
        income = _tx(
            bog,
            date(2026, 9, 10),
            Decimal("417.87"),
            FinancialTransaction.KIND_INCOME,
            "income",
        )

        sync_flowwow_bog_transfers()
        withdrawal.refresh_from_db()
        income.refresh_from_db()
        withdrawal_updated = withdrawal.updated_at
        income_updated = income.updated_at

        sync_flowwow_bog_transfers()

        withdrawal.refresh_from_db()
        income.refresh_from_db()
        self.assertEqual(withdrawal.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(income.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(withdrawal.matched_transaction_id, income.pk)
        self.assertEqual(income.matched_transaction_id, withdrawal.pk)
        self.assertEqual(withdrawal.updated_at, withdrawal_updated)
        self.assertEqual(income.updated_at, income_updated)
