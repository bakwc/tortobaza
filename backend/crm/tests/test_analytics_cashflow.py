from datetime import date
from decimal import Decimal

from django.test import TestCase

from crm.analytics import cashflow
from crm.models import ExchangeRateSnapshot, FinancialAccount, FinancialTransaction


def _account(name: str, currency: str) -> FinancialAccount:
    return FinancialAccount.objects.create(
        name=name,
        kind=FinancialAccount.KIND_BANK,
        currency=currency,
    )


def _tx(
    account: FinancialAccount,
    day: date,
    amount: str,
    kind: str,
    income_type: str,
    expense_type: str,
) -> FinancialTransaction:
    return FinancialTransaction.objects.create(
        account=account,
        date=day,
        amount=Decimal(amount),
        kind=kind,
        income_type=income_type,
        expense_type=expense_type,
    )


class CashflowTests(TestCase):
    def test_sections_reconcile(self):
        ExchangeRateSnapshot.objects.create(
            rates_date=date(2026, 10, 1),
            rates={"USD": "2.50"},
        )
        gel = _account("GEL", "GEL")
        usd = _account("USD", "USD")
        _tx(gel, date(2026, 9, 15), "100.00", FinancialTransaction.KIND_INCOME, FinancialTransaction.INCOME_CASH, "")
        _tx(gel, date(2026, 9, 16), "-10.00", FinancialTransaction.KIND_TRANSFER, "", "")
        _tx(gel, date(2026, 9, 16), "10.00", FinancialTransaction.KIND_TRANSFER, "", "")
        _tx(gel, date(2026, 10, 1), "10.00", FinancialTransaction.KIND_INCOME, FinancialTransaction.INCOME_ONLINE, "")
        _tx(usd, date(2026, 10, 2), "4.00", FinancialTransaction.KIND_INCOME, FinancialTransaction.INCOME_ONLINE, "")
        _tx(gel, date(2026, 10, 3), "30.00", FinancialTransaction.KIND_INCOME, FinancialTransaction.INCOME_CASH, "")
        _tx(gel, date(2026, 10, 4), "40.00", FinancialTransaction.KIND_INCOME, FinancialTransaction.INCOME_TRANSFER, "")
        _tx(gel, date(2026, 10, 5), "-5.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_SALARY)
        _tx(gel, date(2026, 10, 6), "-6.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_RENT)
        _tx(gel, date(2026, 10, 7), "-7.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_PRODUCTS)
        _tx(gel, date(2026, 10, 8), "-8.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_CONSUMABLES)
        _tx(gel, date(2026, 10, 9), "-9.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_FEES)
        _tx(gel, date(2026, 10, 10), "-1.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_TAXI)
        _tx(gel, date(2026, 10, 11), "-2.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_GASOLINE)
        _tx(gel, date(2026, 10, 12), "-3.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_MARKETING)
        _tx(gel, date(2026, 10, 13), "-4.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_TRAINING)
        _tx(gel, date(2026, 10, 14), "-50.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_EQUIPMENT)
        _tx(gel, date(2026, 10, 15), "70.00", FinancialTransaction.KIND_INVESTMENT, "", "")
        _tx(gel, date(2026, 10, 16), "-15.00", FinancialTransaction.KIND_WITHDRAWAL, "", "")
        _tx(gel, date(2026, 10, 17), "11.00", FinancialTransaction.KIND_INCOME, "", "")
        _tx(gel, date(2026, 10, 18), "-12.00", FinancialTransaction.KIND_EXPENSE, "", "")
        _tx(gel, date(2026, 10, 19), "-1.00", FinancialTransaction.KIND_CORRECTION, "", "")
        _tx(gel, date(2026, 10, 20), "3.00", FinancialTransaction.KIND_OTHER, "", "")
        _tx(gel, date(2026, 10, 21), "-20.00", FinancialTransaction.KIND_TRANSFER, "", "")
        _tx(usd, date(2026, 10, 21), "10.00", FinancialTransaction.KIND_TRANSFER, "", "")
        _tx(gel, date(2026, 11, 1), "1000.00", FinancialTransaction.KIND_INCOME, FinancialTransaction.INCOME_CASH, "")

        report = cashflow("2026-10")

        self.assertEqual(report["opening"], "100.00")
        self.assertEqual(
            report["operating"]["inflows"],
            [
                {"key": "online", "amount": "20.00"},
                {"key": "cash", "amount": "30.00"},
                {"key": "transfer", "amount": "40.00"},
                {"key": "", "amount": "11.00"},
            ],
        )
        self.assertEqual(
            report["operating"]["outflows"],
            [
                {"key": "salary", "amount": "-5.00"},
                {"key": "rent", "amount": "-6.00"},
                {"key": "products", "amount": "-7.00"},
                {"key": "consumables", "amount": "-8.00"},
                {"key": "fees", "amount": "-9.00"},
                {"key": "taxi", "amount": "-1.00"},
                {"key": "gasoline", "amount": "-2.00"},
                {"key": "marketing", "amount": "-3.00"},
                {"key": "training", "amount": "-4.00"},
                {"key": "", "amount": "-12.00"},
            ],
        )
        self.assertEqual(report["operating"]["total"], "44.00")
        self.assertEqual(report["investing"], {"lines": [{"key": "equipment", "amount": "-50.00"}], "total": "-50.00"})
        self.assertEqual(
            report["financing"],
            {
                "lines": [
                    {"key": "investment", "amount": "70.00"},
                    {"key": "withdrawal", "amount": "-15.00"},
                ],
                "total": "55.00",
            },
        )
        self.assertEqual(
            report["unclassified"],
            {
                "lines": [
                    {"key": "correction", "amount": "-1.00"},
                    {"key": "other", "amount": "3.00"},
                ],
                "total": "2.00",
            },
        )
        self.assertEqual(report["net"], "51.00")
        self.assertEqual(report["transfers"], "5.00")
        self.assertEqual(report["closing"], "156.00")
        self.assertEqual(
            Decimal(report["closing"]),
            Decimal(report["opening"]) + Decimal(report["net"]) + Decimal(report["transfers"]),
        )
