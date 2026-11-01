from datetime import datetime
from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from openpyxl import Workbook

from crm.models import (
    FinancialAccount,
    FinancialTransaction,
    FinancialTransactionRule,
    FinancialTransactionRuleCondition,
)
from crm.tbc_statement import import_tbc_statement

HEADERS = [
    "Дата",
    "Описание операции",
    "Дополнительная информация",
    "Списание, GEL",
    "Поступление, GEL",
    "Остаток, GEL",
    "Стр. PDF",
]
INCOME_OPERATION = "Private transfer within TBC"
INCOME_ADDITIONAL = "ავთანდილ გორგაძე, TBCBGE22, GE29TB7649345064300130"
EXPENSE_OPERATION = "POS - Vip Pay*YANDEX.GO, 4.70 GEL, Sep 1 2026 8:26PM"
EXPENSE_ADDITIONAL = "TBCBank merchant, TBCBGE22, GE35TB0002511341111111"
ALT_HEADERS = [
    "Дата",
    "Назначение",
    "Дополнительная информация",
    "Расход, GEL",
    "Приход, GEL",
    "Остаток, GEL",
]
INCOME_EXTERNAL_ID = (
    "2026-09-02|Private transfer within TBC|"
    "ავთანდილ გორგაძე, TBCBGE22, GE29TB7649345064300130|90.00"
)
EXPENSE_EXTERNAL_ID = (
    "2026-09-02|POS - Vip Pay*YANDEX.GO, 4.70 GEL, Sep 1 2026 8:26PM|"
    "TBCBank merchant, TBCBGE22, GE35TB0002511341111111|-4.70"
)


def _statement(rows: list[dict]) -> BytesIO:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Операции"
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


def _statement_with_headers(headers: list[str], rows: list[dict]) -> BytesIO:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Операции"
    for index, header in enumerate(headers, start=1):
        worksheet.cell(1, index, header)
    for offset, row in enumerate(rows):
        excel_row = 2 + offset
        for index, header in enumerate(headers, start=1):
            worksheet.cell(excel_row, index, row[header])
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


NATIVE_HEADERS = [
    "თარიღი\nDate",
    "დანიშნულება\nDescription",
    "დამატებითი ინფორმაცია\nAdditional Information",
    "გასული თანხა\nPaid Out",
    "შემოსული თანხა\nPaid In",
    "ბალანსი\nBalance",
]


def _native_statement(rows: list[dict]) -> BytesIO:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Statement"
    worksheet.cell(1, 1, "Account Statement:")
    worksheet.cell(2, 1, "Account:")
    worksheet.cell(2, 2, "GE07TB7154245068100036")
    for index, header in enumerate(NATIVE_HEADERS, start=1):
        worksheet.cell(4, index, header)
    for offset, row in enumerate(rows):
        excel_row = 5 + offset
        for index, header in enumerate(NATIVE_HEADERS, start=1):
            worksheet.cell(excel_row, index, row[header])
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def _account(name: str, bank_name: str) -> FinancialAccount:
    return FinancialAccount.objects.create(
        name=name,
        kind=FinancialAccount.KIND_BANK,
        bank_name=bank_name,
        currency="GEL",
    )


def _income() -> dict:
    return {
        "Дата": datetime(2026, 9, 2),
        "Описание операции": INCOME_OPERATION,
        "Дополнительная информация": INCOME_ADDITIONAL,
        "Списание, GEL": None,
        "Поступление, GEL": 90,
        "Остаток, GEL": 368.93,
        "Стр. PDF": 1,
    }


def _expense() -> dict:
    return {
        "Дата": datetime(2026, 9, 2),
        "Описание операции": EXPENSE_OPERATION,
        "Дополнительная информация": EXPENSE_ADDITIONAL,
        "Списание, GEL": 4.7,
        "Поступление, GEL": None,
        "Остаток, GEL": 358.13,
        "Стр. PDF": 2,
    }


class TbcStatementImportTests(TestCase):
    def test_creates_income_and_expense(self):
        account = _account("TBC card", "TBC")
        result = import_tbc_statement(_statement([_income(), _expense()]))
        self.assertEqual(result.error, "")
        self.assertEqual(result.created, 2)
        self.assertEqual(result.skipped, 0)
        income = FinancialTransaction.objects.get(external_id=INCOME_EXTERNAL_ID)
        self.assertEqual(income.account, account)
        self.assertEqual(income.date, datetime(2026, 9, 2).date())
        self.assertEqual(income.amount, Decimal("90.00"))
        self.assertEqual(income.kind, FinancialTransaction.KIND_INCOME)
        self.assertEqual(income.income_type, FinancialTransaction.INCOME_TRANSFER)
        self.assertEqual(income.counterparty_name, "ავთანდილ გორგაძე")
        self.assertEqual(income.counterparty_iban, "GE29TB7649345064300130")
        self.assertEqual(income.description, f"{INCOME_OPERATION} | {INCOME_ADDITIONAL}")
        expense = FinancialTransaction.objects.get(external_id=EXPENSE_EXTERNAL_ID)
        self.assertEqual(expense.account, account)
        self.assertEqual(expense.amount, Decimal("-4.70"))
        self.assertEqual(expense.kind, FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(expense.income_type, "")
        self.assertEqual(expense.counterparty_name, "POS - Vip Pay*YANDEX.GO")
        self.assertEqual(expense.counterparty_iban, "GE35TB0002511341111111")
        self.assertEqual(expense.description, f"{EXPENSE_OPERATION} | {EXPENSE_ADDITIONAL}")

    def test_transfer_expense_keeps_counterparty_from_additional_information(self):
        _account("TBC card", "TBC")
        row = _expense()
        row["Описание операции"] = "Private transfer within TBC"
        row["Дополнительная информация"] = INCOME_ADDITIONAL
        result = import_tbc_statement(_statement([row]))
        self.assertEqual(result.error, "")
        expense = FinancialTransaction.objects.get()
        self.assertEqual(expense.kind, FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(expense.counterparty_name, "ავთანდილ გორგაძე")

    def test_reimport_updates_card_expense_counterparty(self):
        _account("TBC card", "TBC")
        import_tbc_statement(_statement([_expense()]))
        expense = FinancialTransaction.objects.get(external_id=EXPENSE_EXTERNAL_ID)
        expense.counterparty_name = (
            "თიბისი ბანკის MC ბარათებით სავაჭრო ობიექტებში სხვა ბანკის ტერმინალებში"
        )
        expense.save(update_fields=["counterparty_name"])
        again = import_tbc_statement(_statement([_expense(), _income()]))
        self.assertEqual(again.error, "")
        self.assertEqual(again.created, 1)
        self.assertEqual(again.skipped, 1)
        expense.refresh_from_db()
        self.assertEqual(expense.counterparty_name, "POS - Vip Pay*YANDEX.GO")
        income = FinancialTransaction.objects.get(external_id=INCOME_EXTERNAL_ID)
        self.assertEqual(income.counterparty_name, "ავთანდილ გორგაძე")

    def test_skips_duplicates(self):
        _account("TBC card", "TBC")
        statement = _statement([_income(), _expense()])
        import_tbc_statement(statement)
        statement.seek(0)
        again = import_tbc_statement(statement)
        self.assertEqual(again.error, "")
        self.assertEqual(again.created, 0)
        self.assertEqual(again.skipped, 2)
        self.assertEqual(FinancialTransaction.objects.count(), 2)
        fresh = _expense()
        fresh["Списание, GEL"] = 18
        mixed = import_tbc_statement(_statement([_income(), _income(), fresh]))
        self.assertEqual(mixed.error, "")
        self.assertEqual(mixed.created, 1)
        self.assertEqual(mixed.skipped, 2)
        self.assertEqual(FinancialTransaction.objects.count(), 3)

    def test_applies_expense_rule(self):
        _account("TBC card", "TBC")
        rule = FinancialTransactionRule.objects.create(
            name="Yandex",
            expense_type=FinancialTransaction.EXPENSE_FEES,
            priority=1,
            operator=FinancialTransactionRule.OPERATOR_OR,
            is_active=True,
        )
        FinancialTransactionRuleCondition.objects.create(
            rule=rule,
            field=FinancialTransactionRuleCondition.FIELD_DESCRIPTION,
            pattern="*YANDEX.GO*",
        )
        result = import_tbc_statement(_statement([_income(), _expense()]))
        self.assertEqual(result.error, "")
        expense = FinancialTransaction.objects.get(external_id=EXPENSE_EXTERNAL_ID)
        income = FinancialTransaction.objects.get(external_id=INCOME_EXTERNAL_ID)
        self.assertEqual(expense.expense_type, FinancialTransaction.EXPENSE_FEES)
        self.assertEqual(income.expense_type, "")

    def test_missing_account_creates_nothing(self):
        _account("TBC", "")
        result = import_tbc_statement(_statement([_income(), _expense()]))
        self.assertEqual(result.error, "TBC account not found")
        self.assertEqual(result.created, 0)
        self.assertEqual(FinancialTransaction.objects.count(), 0)

    def test_ambiguous_account_creates_nothing(self):
        _account("TBC card", "TBC")
        _account("TBC business", "TBC")
        result = import_tbc_statement(_statement([_income()]))
        self.assertEqual(result.error, "TBC account matched more than once")
        self.assertEqual(result.created, 0)
        self.assertEqual(FinancialTransaction.objects.count(), 0)

    def test_both_amounts_creates_nothing(self):
        _account("TBC card", "TBC")
        row = _income()
        row["Списание, GEL"] = 10
        result = import_tbc_statement(_statement([row, _expense()]))
        self.assertEqual(result.error, "Row 2: both debit and credit are set")
        self.assertEqual(result.created, 0)
        self.assertEqual(FinancialTransaction.objects.count(), 0)

    def test_empty_amounts_creates_nothing(self):
        _account("TBC card", "TBC")
        row = _income()
        row["Поступление, GEL"] = None
        result = import_tbc_statement(_statement([row, _expense()]))
        self.assertEqual(result.error, "Row 2: debit and credit are empty")
        self.assertEqual(result.created, 0)
        self.assertEqual(FinancialTransaction.objects.count(), 0)

    def test_invalid_additional_information_creates_nothing(self):
        _account("TBC card", "TBC")
        row = _income()
        row["Дополнительная информация"] = "only a name"
        result = import_tbc_statement(_statement([row, _expense()]))
        self.assertEqual(result.error, "Row 2: additional information must have three parts")
        self.assertEqual(result.created, 0)
        self.assertEqual(FinancialTransaction.objects.count(), 0)

    def test_missing_iban_creates_nothing(self):
        _account("TBC card", "TBC")
        row = _income()
        row["Дополнительная информация"] = "ავთანდილ გორგაძე, TBCBGE22,"
        result = import_tbc_statement(_statement([row]))
        self.assertEqual(result.error, "Row 2: missing IBAN")
        self.assertEqual(result.created, 0)
        self.assertEqual(FinancialTransaction.objects.count(), 0)

    def test_alternate_column_names(self):
        _account("TBC card", "TBC")
        income_additional = "შპს ქიფზ.მი, 405618915, TBCBGE22, GE82TB7753436020100010"
        expense_additional = "პოპოვიჩ ანდრიი, UA,GM493432, CBASGE22, GE17BS0000097608945002"
        expense_operation = "POS - LTD KEEPZ.ME*YANDEX GO, 4.80 GEL, Oct 4 2026 4:06PM"
        result = import_tbc_statement(
            _statement_with_headers(
                ALT_HEADERS,
                [
                    {
                        "Дата": datetime(2026, 10, 1),
                        "Назначение": "COST OF SERVICES",
                        "Дополнительная информация": income_additional,
                        "Расход, GEL": None,
                        "Приход, GEL": 75,
                        "Остаток, GEL": 2633.8,
                    },
                    {
                        "Дата": datetime(2026, 10, 5),
                        "Назначение": expense_operation,
                        "Дополнительная информация": expense_additional,
                        "Расход, GEL": 4.8,
                        "Приход, GEL": None,
                        "Остаток, GEL": 1373.98,
                    },
                ],
            )
        )
        self.assertEqual(result.error, "")
        self.assertEqual(result.created, 2)
        income = FinancialTransaction.objects.get(kind=FinancialTransaction.KIND_INCOME)
        self.assertEqual(income.amount, Decimal("75.00"))
        self.assertEqual(income.counterparty_name, "შპს ქიფზ.მი")
        self.assertEqual(income.counterparty_iban, "GE82TB7753436020100010")
        self.assertEqual(income.description, f"COST OF SERVICES | {income_additional}")
        expense = FinancialTransaction.objects.get(kind=FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(expense.amount, Decimal("-4.80"))
        self.assertEqual(expense.counterparty_name, "POS - LTD KEEPZ.ME*YANDEX GO")
        self.assertEqual(expense.counterparty_iban, "GE17BS0000097608945002")
        self.assertEqual(expense.description, f"{expense_operation} | {expense_additional}")

    def test_native_statement_export(self):
        _account("TBC card", "TBC")
        income_additional = "ი/მ სელეჰეი მარკო, BAGAGE22, GE72BG0000000611931871"
        expense_operation = (
            "POS - LTD KEEPZ.ME*YANDEX GO, 5.20 GEL, Sep 30 2026\n3:52PM, ტრანსპორტი"
        )
        expense_additional = (
            "TBCBank merchant, TBCBGE22,\nGE28TB0004511348888888"
        )
        result = import_tbc_statement(
            _native_statement(
                [
                    {
                        "თარიღი\nDate": "01/10/2026",
                        "დანიშნულება\nDescription": "COST OF SERVICES",
                        "დამატებითი ინფორმაცია\nAdditional Information": income_additional,
                        "გასული თანხა\nPaid Out": None,
                        "შემოსული თანხა\nPaid In": "75.00",
                        "ბალანსი\nBalance": "2633.80",
                    },
                    {
                        "თარიღი\nDate": "01/10/2026",
                        "დანიშნულება\nDescription": expense_operation,
                        "დამატებითი ინფორმაცია\nAdditional Information": expense_additional,
                        "გასული თანხა\nPaid Out": "5.20",
                        "შემოსული თანხა\nPaid In": None,
                        "ბალანსი\nBalance": "2628.60",
                    },
                ]
            )
        )
        expense_operation_line = expense_operation.replace("\n", " ")
        expense_additional_line = "TBCBank merchant, TBCBGE22, GE28TB0004511348888888"
        self.assertEqual(result.error, "")
        self.assertEqual(result.created, 2)
        income = FinancialTransaction.objects.get(kind=FinancialTransaction.KIND_INCOME)
        self.assertEqual(income.date, datetime(2026, 10, 1).date())
        self.assertEqual(income.amount, Decimal("75.00"))
        self.assertEqual(income.counterparty_name, "ი/მ სელეჰეი მარკო")
        self.assertEqual(income.counterparty_iban, "GE72BG0000000611931871")
        self.assertEqual(income.external_id, f"2026-10-01|COST OF SERVICES|{income_additional}|75.00")
        expense = FinancialTransaction.objects.get(kind=FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(expense.amount, Decimal("-5.20"))
        self.assertEqual(expense.counterparty_name, "POS - LTD KEEPZ.ME*YANDEX GO")
        self.assertEqual(expense.counterparty_iban, "GE28TB0004511348888888")
        self.assertEqual(
            expense.external_id,
            f"2026-10-01|{expense_operation_line}|{expense_additional_line}|-5.20",
        )
        self.assertNotIn("\n", expense.description)

    def test_native_reimport_matches_old_external_id(self):
        _account("TBC card", "TBC")
        first = import_tbc_statement(_statement([_income()]))
        self.assertEqual(first.error, "")
        self.assertEqual(first.created, 1)
        again = import_tbc_statement(
            _native_statement(
                [
                    {
                        "თარიღი\nDate": "02/09/2026",
                        "დანიშნულება\nDescription": INCOME_OPERATION,
                        "დამატებითი ინფორმაცია\nAdditional Information": (
                            "ავთანდილ გორგაძე, TBCBGE22,\nGE29TB7649345064300130"
                        ),
                        "გასული თანხა\nPaid Out": None,
                        "შემოსული თანხა\nPaid In": "90.00",
                        "ბალანსი\nBalance": "368.93",
                    }
                ]
            )
        )
        self.assertEqual(again.error, "")
        self.assertEqual(again.created, 0)
        self.assertEqual(again.skipped, 1)
        self.assertEqual(FinancialTransaction.objects.count(), 1)
        income = FinancialTransaction.objects.get()
        self.assertEqual(income.external_id, INCOME_EXTERNAL_ID)
