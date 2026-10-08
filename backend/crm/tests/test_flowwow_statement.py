from datetime import date
from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from openpyxl import Workbook

from crm.flowwow_statement import import_flowwow_statement
from crm.models import FinancialAccount, FinancialTransaction

HEADERS = [
    "Contract number",
    "Contract date",
    "Order number",
    "Order payment date",
    "Order delivery date",
    "Transaction type",
    "Transaction amount",
    "Transaction currency",
    "Transaction rate",
    "Transaction amount in shop currency",
]


def _statement(rows: list[dict]) -> BytesIO:
    workbook = Workbook()
    worksheet = workbook.active
    for index, header in enumerate(HEADERS, start=1):
        worksheet.cell(1, index, header)
    for offset, row in enumerate(rows):
        excel_row = 2 + offset
        for index, header in enumerate(HEADERS, start=1):
            worksheet.cell(excel_row, index, row[header])
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def _account() -> FinancialAccount:
    return FinancialAccount.objects.create(
        name="Flowwow",
        kind=FinancialAccount.KIND_VIRTUAL,
        currency="GEL",
    )


def _row(
    order_number: int,
    payment_date: str,
    delivery_date: str | None,
    transaction_type: str,
    amount: float,
    currency: str,
    shop_amount: float,
) -> dict:
    return {
        "Contract number": "G-100222/1",
        "Contract date": "05.03.2024",
        "Order number": order_number,
        "Order payment date": payment_date,
        "Order delivery date": delivery_date,
        "Transaction type": transaction_type,
        "Transaction amount": amount,
        "Transaction currency": currency,
        "Transaction rate": 1.0,
        "Transaction amount in shop currency": shop_amount,
    }


def _paid() -> dict:
    return _row(
        26136332,
        "07.10.2026 13:00:24",
        "07.10.2026 13:00:24",
        "Paid by customer",
        75.0,
        "GEL",
        75.0,
    )


def _usd_paid() -> dict:
    return _row(
        26128282,
        "06.10.2026 18:43:11",
        "06.10.2026 18:43:11",
        "Paid by customer",
        29.77,
        "USD",
        75.0,
    )


def _fee() -> dict:
    return _row(
        26136332,
        "07.10.2026 13:00:24",
        "07.10.2026 13:00:24",
        "Card processing fee",
        -0.3,
        "GEL",
        -0.3,
    )


def _second_fee() -> dict:
    return _row(
        26136332,
        "07.10.2026 13:00:24",
        "07.10.2026 13:00:24",
        "Card processing fee",
        -2.25,
        "GEL",
        -2.25,
    )


def _withdrawal() -> dict:
    return _row(
        2450790,
        "06.10.2026 12:08:51",
        None,
        "Withdrawal",
        -391.13,
        "GEL",
        -391.13,
    )


class FlowwowStatementImportTests(TestCase):
    def test_creates_income_expense_and_withdrawal(self):
        account = _account()
        result = import_flowwow_statement(
            _statement([_paid(), _usd_paid(), _fee(), _second_fee(), _withdrawal()])
        )
        self.assertEqual(result.error, "")
        self.assertEqual(result.created, 5)
        self.assertEqual(result.skipped, 0)
        income = FinancialTransaction.objects.get(
            external_id="26136332|Paid by customer|2026-10-07 13:00:24|75.00"
        )
        self.assertEqual(income.account, account)
        self.assertEqual(income.date, date(2026, 10, 7))
        self.assertEqual(income.amount, Decimal("75.00"))
        self.assertEqual(income.kind, FinancialTransaction.KIND_INCOME)
        self.assertEqual(income.income_type, "")
        self.assertEqual(income.expense_type, "")
        self.assertEqual(income.counterparty_name, "Flowwow")
        self.assertEqual(income.description, "Paid by customer")
        usd_income = FinancialTransaction.objects.get(
            external_id="26128282|Paid by customer|2026-10-06 18:43:11|75.00"
        )
        self.assertEqual(usd_income.amount, Decimal("75.00"))
        self.assertEqual(usd_income.kind, FinancialTransaction.KIND_INCOME)
        self.assertEqual(usd_income.description, "Paid by customer 29.77 USD")
        fee = FinancialTransaction.objects.get(
            external_id="26136332|Card processing fee|2026-10-07 13:00:24|-0.30"
        )
        self.assertEqual(fee.amount, Decimal("-0.30"))
        self.assertEqual(fee.kind, FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(fee.expense_type, "")
        second_fee = FinancialTransaction.objects.get(
            external_id="26136332|Card processing fee|2026-10-07 13:00:24|-2.25"
        )
        self.assertEqual(second_fee.amount, Decimal("-2.25"))
        self.assertEqual(second_fee.kind, FinancialTransaction.KIND_EXPENSE)
        withdrawal = FinancialTransaction.objects.get(
            external_id="2450790|Withdrawal|2026-10-06 12:08:51|-391.13"
        )
        self.assertEqual(withdrawal.date, date(2026, 10, 6))
        self.assertEqual(withdrawal.amount, Decimal("-391.13"))
        self.assertEqual(withdrawal.kind, FinancialTransaction.KIND_WITHDRAWAL)
        self.assertEqual(withdrawal.description, "Withdrawal")

    def test_skips_duplicates(self):
        _account()
        statement = _statement([_paid(), _fee(), _withdrawal()])
        import_flowwow_statement(statement)
        statement.seek(0)
        again = import_flowwow_statement(statement)
        self.assertEqual(again.error, "")
        self.assertEqual(again.created, 0)
        self.assertEqual(again.skipped, 3)
        self.assertEqual(FinancialTransaction.objects.count(), 3)
        fresh = _second_fee()
        mixed = import_flowwow_statement(_statement([_paid(), _paid(), fresh]))
        self.assertEqual(mixed.error, "")
        self.assertEqual(mixed.created, 1)
        self.assertEqual(mixed.skipped, 2)
        self.assertEqual(FinancialTransaction.objects.count(), 4)

    def test_missing_account_creates_nothing(self):
        result = import_flowwow_statement(_statement([_paid(), _fee()]))
        self.assertEqual(result.error, "Flowwow account not found")
        self.assertEqual(result.created, 0)
        self.assertEqual(FinancialTransaction.objects.count(), 0)

    def test_unknown_type_creates_nothing(self):
        _account()
        row = _paid()
        row["Transaction type"] = "Refund"
        result = import_flowwow_statement(_statement([row, _fee()]))
        self.assertEqual(result.error, "Row 2: unknown transaction type")
        self.assertEqual(result.created, 0)
        self.assertEqual(FinancialTransaction.objects.count(), 0)
