from datetime import date
from decimal import Decimal

from django.test import TestCase

from crm.analytics import pnl
from crm.models import FinancialAccount, FinancialTransaction
from inventory.models import StockMovement, Supply, SupplyLine, SupplyTransaction
from menu.models import UNIT_GRAM, Ingredient
from tortobaza.finance_db import use_finance_db


def _account() -> FinancialAccount:
    return FinancialAccount.objects.create(
        name="GEL",
        kind=FinancialAccount.KIND_BANK,
        currency="GEL",
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


def _ingredient(name: str, avg_cost: str) -> Ingredient:
    return Ingredient.objects.create(name=name, unit=UNIT_GRAM, avg_cost=Decimal(avg_cost))


def _movement(ingredient: Ingredient, day: date, kind: str, quantity: str, unit_cost: str) -> StockMovement:
    return StockMovement.objects.create(
        ingredient=ingredient,
        date=day,
        kind=kind,
        quantity=Decimal(quantity),
        unit_cost=Decimal(unit_cost),
    )


def _paid_supply(
    ingredient: Ingredient,
    day: date,
    payment: FinancialTransaction,
    totals: tuple[str, ...],
) -> Supply:
    supply = Supply.objects.create(date=day)
    for total in totals:
        SupplyLine.objects.create(
            supply=supply,
            ingredient=ingredient,
            quantity=Decimal("1"),
            total=Decimal(total),
        )
    SupplyTransaction.objects.create(supply=supply, financial_transaction=payment)
    return supply


class PnlTests(TestCase):
    databases = {"default", "personal"}
    def test_unlinked_operations_and_skipped_kinds(self):
        account = _account()
        _tx(account, date(2026, 10, 10), "100.00", FinancialTransaction.KIND_INCOME, FinancialTransaction.INCOME_CASH, "")
        _tx(account, date(2026, 10, 11), "-6.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_RENT)
        _tx(account, date(2026, 10, 12), "-7.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_PRODUCTS)
        _tx(account, date(2026, 10, 13), "-50.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_EQUIPMENT)
        _tx(account, date(2026, 10, 14), "-20.00", FinancialTransaction.KIND_TRANSFER, "", "")
        _tx(account, date(2026, 10, 15), "-1.00", FinancialTransaction.KIND_CORRECTION, "", "")
        _tx(account, date(2026, 10, 16), "70.00", FinancialTransaction.KIND_INVESTMENT, "", "")
        _tx(account, date(2026, 10, 17), "-15.00", FinancialTransaction.KIND_WITHDRAWAL, "", "")

        report = pnl("2026-10")

        self.assertEqual(report["income"], {"lines": [{"key": "cash", "amount": "100.00"}], "total": "100.00"})
        self.assertEqual(report["expenses"]["lines"], [{"key": "rent", "amount": "-6.00"}])
        self.assertEqual(
            report["expenses"]["cogs"],
            {"lines": [{"key": "unlinked_products", "amount": "-7.00"}], "total": "-7.00"},
        )
        self.assertEqual(report["expenses"]["total"], "-13.00")
        self.assertEqual(
            report["unclassified"],
            {"lines": [{"key": "correction", "amount": "-1.00"}], "total": "-1.00"},
        )
        self.assertEqual(report["profit"], "86.00")

    def test_linked_supply_gap_and_later_order(self):
        account = _account()
        flour = _ingredient("Мука", "0")
        payment = _tx(
            account,
            date(2026, 11, 10),
            "-100.00",
            FinancialTransaction.KIND_EXPENSE,
            "",
            FinancialTransaction.EXPENSE_PRODUCTS,
        )
        _paid_supply(flour, date(2026, 10, 20), payment, ("40.00", "50.00"))
        _movement(flour, date(2026, 12, 1), StockMovement.KIND_ORDER, "-1", "30")

        october = pnl("2026-10")
        november = pnl("2026-11")
        december = pnl("2026-12")

        self.assertEqual(
            october["expenses"]["cogs"],
            {"lines": [{"key": "supply_gap", "amount": "-10.00"}], "total": "-10.00"},
        )
        self.assertEqual(october["profit"], "-10.00")
        self.assertEqual(november["expenses"]["cogs"], {"lines": [], "total": "0.00"})
        self.assertEqual(november["expenses"]["lines"], [])
        self.assertEqual(november["profit"], "0.00")
        self.assertEqual(
            december["expenses"]["cogs"],
            {"lines": [{"key": "orders", "amount": "-30.00"}], "total": "-30.00"},
        )
        self.assertEqual(december["profit"], "-30.00")

    def test_supply_received_above_payment(self):
        account = _account()
        flour = _ingredient("Сахар", "0")
        payment = _tx(
            account,
            date(2026, 10, 5),
            "-80.00",
            FinancialTransaction.KIND_EXPENSE,
            "",
            FinancialTransaction.EXPENSE_PRODUCTS,
        )
        _paid_supply(flour, date(2026, 10, 5), payment, ("60.00", "50.00"))

        report = pnl("2026-10")

        self.assertEqual(
            report["expenses"]["cogs"],
            {"lines": [{"key": "supply_gap", "amount": "30.00"}], "total": "30.00"},
        )
        self.assertEqual(report["profit"], "30.00")

    def test_salary_cutoff(self):
        account = _account()
        _tx(account, date(2026, 10, 3), "-10.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_SALARY)
        _tx(account, date(2026, 10, 4), "-20.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_SALARY)
        _tx(account, date(2026, 11, 2), "-30.00", FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_SALARY)

        september = pnl("2026-09")
        october = pnl("2026-10")
        november = pnl("2026-11")

        self.assertEqual(september["expenses"]["lines"], [{"key": "salary", "amount": "-10.00"}])
        self.assertEqual(september["profit"], "-10.00")
        self.assertEqual(october["expenses"]["lines"], [{"key": "salary", "amount": "-50.00"}])
        self.assertEqual(october["profit"], "-50.00")
        self.assertEqual(november["expenses"]["lines"], [])
        self.assertEqual(november["profit"], "0.00")

    def test_inventory_shift_and_surplus_without_supply(self):
        flour = _ingredient("Изюм", "5")
        _movement(flour, date(2026, 11, 2), StockMovement.KIND_INVENTORY, "2", "5")
        _movement(flour, date(2026, 11, 4), StockMovement.KIND_INVENTORY, "-1", "4")

        october = pnl("2026-10")
        november = pnl("2026-11")

        self.assertEqual(
            october["expenses"]["cogs"],
            {"lines": [{"key": "inventory", "amount": "10.00"}], "total": "10.00"},
        )
        self.assertEqual(october["profit"], "10.00")
        self.assertEqual(
            november["expenses"]["cogs"],
            {"lines": [{"key": "inventory", "amount": "-4.00"}], "total": "-4.00"},
        )
        self.assertEqual(november["profit"], "-4.00")

    def test_production_stays_on_the_warehouse(self):
        flour = _ingredient("Масло", "3")
        _movement(flour, date(2026, 10, 5), StockMovement.KIND_PRODUCTION_OUT, "-10", "3")
        _movement(flour, date(2026, 10, 5), StockMovement.KIND_PRODUCTION_IN, "10", "3")

        report = pnl("2026-10")

        self.assertEqual(report["expenses"]["cogs"], {"lines": [], "total": "0.00"})
        self.assertEqual(report["profit"], "0.00")

    def test_ceo_compensation_stays_in_its_month(self):
        with use_finance_db("personal"):
            gel = FinancialAccount.objects.create(
                name="BOG darya GEL",
                kind=FinancialAccount.KIND_BANK,
                currency="GEL",
            )
            other = FinancialAccount.objects.create(
                name="Other",
                kind=FinancialAccount.KIND_BANK,
                currency="GEL",
            )
            _tx(gel, date(2026, 9, 10), "-7.00", FinancialTransaction.KIND_EXPENSE, "", "")
            _tx(gel, date(2026, 10, 2), "-15.00", FinancialTransaction.KIND_EXPENSE, "", "")
            _tx(gel, date(2026, 11, 2), "-8.00", FinancialTransaction.KIND_EXPENSE, "", "")
            _tx(other, date(2026, 10, 10), "-100.00", FinancialTransaction.KIND_EXPENSE, "", "")
            _tx(gel, date(2026, 10, 11), "40.00", FinancialTransaction.KIND_INCOME, FinancialTransaction.INCOME_CASH, "")

        september = pnl("2026-09")
        october = pnl("2026-10")
        november = pnl("2026-11")

        self.assertEqual(september["expenses"]["lines"], [{"key": "ceo_compensation", "amount": "-7.00"}])
        self.assertEqual(september["profit"], "-7.00")
        self.assertEqual(october["expenses"]["lines"], [{"key": "ceo_compensation", "amount": "-15.00"}])
        self.assertEqual(october["profit"], "-15.00")
        self.assertEqual(november["expenses"]["lines"], [{"key": "ceo_compensation", "amount": "-8.00"}])
        self.assertEqual(november["profit"], "-8.00")
