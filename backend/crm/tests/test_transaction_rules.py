from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase

from crm.models import (
    FinancialAccount,
    FinancialTransaction,
    FinancialTransactionRule,
    FinancialTransactionRuleCondition,
)
from crm.transaction_rules import assign_expense_types, categorize_uncategorized_expenses


def _account(name: str, iban: str) -> FinancialAccount:
    return FinancialAccount.objects.create(
        name=name,
        kind=FinancialAccount.KIND_BANK,
        iban=iban,
        currency="GEL",
    )


def _transaction(
    account: FinancialAccount,
    kind: str,
    description: str,
    counterparty_name: str,
    counterparty_iban: str,
    expense_type: str,
) -> FinancialTransaction:
    return FinancialTransaction.objects.create(
        account=account,
        date=date(2026, 10, 1),
        amount=Decimal("-10.00"),
        kind=kind,
        description=description,
        counterparty_name=counterparty_name,
        counterparty_iban=counterparty_iban,
        expense_type=expense_type,
    )


def _rule(
    name: str,
    expense_type: str,
    priority: int,
    operator: str,
    is_active: bool,
    conditions: list[tuple[str, str]],
) -> FinancialTransactionRule:
    rule = FinancialTransactionRule.objects.create(
        name=name,
        expense_type=expense_type,
        priority=priority,
        operator=operator,
        is_active=is_active,
    )
    for field, pattern in conditions:
        FinancialTransactionRuleCondition.objects.create(rule=rule, field=field, pattern=pattern)
    return rule


class ExpenseRuleTests(TestCase):
    def test_matches_wildcard_case_and_operators(self):
        account = _account("Main", "GE00TB0000000000000001")
        other = _account("Other", "GE00TB0000000000000002")
        manufactory = _transaction(
            account,
            FinancialTransaction.KIND_EXPENSE,
            "Invoice Manufactory flour",
            "Manufactory Ltd",
            "GE11TB0000000000000099",
            "",
        )
        salary = _transaction(
            account,
            FinancialTransaction.KIND_EXPENSE,
            "October payroll",
            "Nino",
            "ge22tb0000000000000088",
            "",
        )
        fee = _transaction(
            account,
            FinancialTransaction.KIND_EXPENSE,
            "Wire Transfer Fee",
            "",
            "",
            "",
        )
        partial = _transaction(
            account,
            FinancialTransaction.KIND_EXPENSE,
            "Invoice Manufactory sugar",
            "Manufactory Ltd",
            "GE11TB0000000000000099",
            "",
        )
        rent = _transaction(
            other,
            FinancialTransaction.KIND_EXPENSE,
            "October rent",
            "Landlord",
            "GE33TB0000000000000077",
            "",
        )
        income = _transaction(
            account,
            FinancialTransaction.KIND_INCOME,
            "Invoice Manufactory flour",
            "Manufactory Ltd",
            "GE11TB0000000000000099",
            "",
        )
        _rule(
            "Products",
            FinancialTransaction.EXPENSE_PRODUCTS,
            1,
            FinancialTransactionRule.OPERATOR_AND,
            True,
            [
                (FinancialTransactionRuleCondition.FIELD_COUNTERPARTY_NAME, "*manufactory*"),
                (FinancialTransactionRuleCondition.FIELD_DESCRIPTION, "*Flour"),
            ],
        )
        _rule(
            "Salary",
            FinancialTransaction.EXPENSE_SALARY,
            2,
            FinancialTransactionRule.OPERATOR_OR,
            True,
            [
                (FinancialTransactionRuleCondition.FIELD_COUNTERPARTY_IBAN, "GE22TB0000000000000088"),
                (FinancialTransactionRuleCondition.FIELD_DESCRIPTION, "payroll"),
            ],
        )
        _rule(
            "Fees",
            FinancialTransaction.EXPENSE_FEES,
            3,
            FinancialTransactionRule.OPERATOR_OR,
            True,
            [
                (FinancialTransactionRuleCondition.FIELD_DESCRIPTION, "Fee?"),
                (FinancialTransactionRuleCondition.FIELD_DESCRIPTION, "*fee"),
            ],
        )
        _rule(
            "Rent",
            FinancialTransaction.EXPENSE_RENT,
            4,
            FinancialTransactionRule.OPERATOR_AND,
            True,
            [
                (FinancialTransactionRuleCondition.FIELD_ACCOUNT_IBAN, "GE00TB0000000000000002"),
                (FinancialTransactionRuleCondition.FIELD_COUNTERPARTY_NAME, "Landlord"),
            ],
        )
        _rule(
            "Disabled",
            FinancialTransaction.EXPENSE_EQUIPMENT,
            0,
            FinancialTransactionRule.OPERATOR_OR,
            False,
            [(FinancialTransactionRuleCondition.FIELD_DESCRIPTION, "*")],
        )
        _rule(
            "Empty",
            FinancialTransaction.EXPENSE_CONSUMABLES,
            0,
            FinancialTransactionRule.OPERATOR_OR,
            True,
            [],
        )
        assign_expense_types(
            [manufactory, salary, fee, partial, rent, income],
        )
        self.assertEqual(manufactory.expense_type, FinancialTransaction.EXPENSE_PRODUCTS)
        self.assertEqual(salary.expense_type, FinancialTransaction.EXPENSE_SALARY)
        self.assertEqual(fee.expense_type, FinancialTransaction.EXPENSE_FEES)
        self.assertEqual(partial.expense_type, "")
        self.assertEqual(rent.expense_type, FinancialTransaction.EXPENSE_RENT)
        self.assertEqual(income.expense_type, "")

    def test_lower_priority_wins_and_existing_category_stays(self):
        account = _account("Main", "GE00TB0000000000000001")
        expense = _transaction(
            account,
            FinancialTransaction.KIND_EXPENSE,
            "Manufactory",
            "",
            "",
            "",
        )
        categorized = _transaction(
            account,
            FinancialTransaction.KIND_EXPENSE,
            "Manufactory",
            "",
            "",
            FinancialTransaction.EXPENSE_EQUIPMENT,
        )
        payroll = _transaction(
            account,
            FinancialTransaction.KIND_EXPENSE,
            "Payroll",
            "",
            "",
            "",
        )
        _rule(
            "Broad",
            FinancialTransaction.EXPENSE_EQUIPMENT,
            8,
            FinancialTransactionRule.OPERATOR_OR,
            True,
            [(FinancialTransactionRuleCondition.FIELD_DESCRIPTION, "Payroll")],
        )
        _rule(
            "Later",
            FinancialTransaction.EXPENSE_PRODUCTS,
            5,
            FinancialTransactionRule.OPERATOR_OR,
            True,
            [(FinancialTransactionRuleCondition.FIELD_DESCRIPTION, "Manufactory")],
        )
        _rule(
            "Earlier",
            FinancialTransaction.EXPENSE_CONSUMABLES,
            5,
            FinancialTransactionRule.OPERATOR_OR,
            True,
            [(FinancialTransactionRuleCondition.FIELD_DESCRIPTION, "Manufactory")],
        )
        _rule(
            "Salary",
            FinancialTransaction.EXPENSE_SALARY,
            1,
            FinancialTransactionRule.OPERATOR_OR,
            True,
            [(FinancialTransactionRuleCondition.FIELD_DESCRIPTION, "Payroll")],
        )
        first = FinancialTransactionRule.objects.get(name="Later")
        second = FinancialTransactionRule.objects.get(name="Earlier")
        self.assertLess(first.id, second.id)
        assign_expense_types([expense, categorized, payroll])
        self.assertEqual(expense.expense_type, FinancialTransaction.EXPENSE_PRODUCTS)
        self.assertEqual(categorized.expense_type, FinancialTransaction.EXPENSE_EQUIPMENT)
        self.assertEqual(payroll.expense_type, FinancialTransaction.EXPENSE_SALARY)

    def test_question_mark_matches_one_character(self):
        account = _account("Main", "GE00TB0000000000000001")
        expense = _transaction(
            account,
            FinancialTransaction.KIND_EXPENSE,
            "Fees",
            "",
            "",
            "",
        )
        _rule(
            "Fees",
            FinancialTransaction.EXPENSE_FEES,
            1,
            FinancialTransactionRule.OPERATOR_OR,
            True,
            [(FinancialTransactionRuleCondition.FIELD_DESCRIPTION, "Fee?")],
        )
        assign_expense_types([expense])
        self.assertEqual(expense.expense_type, FinancialTransaction.EXPENSE_FEES)

    def test_literal_characters_are_not_wildcards(self):
        account = _account("Main", "GE00TB0000000000000001")
        expense = _transaction(
            account,
            FinancialTransaction.KIND_EXPENSE,
            "FeeX",
            "",
            "",
            "",
        )
        _rule(
            "Fees",
            FinancialTransaction.EXPENSE_FEES,
            1,
            FinancialTransactionRule.OPERATOR_OR,
            True,
            [(FinancialTransactionRuleCondition.FIELD_DESCRIPTION, "Fee.")],
        )
        assign_expense_types([expense])
        self.assertEqual(expense.expense_type, "")

    def test_categorize_updates_only_empty_expenses(self):
        account = _account("Main", "GE00TB0000000000000001")
        other = _account("Other", "GE00TB0000000000000002")
        empty_fee = _transaction(
            account,
            FinancialTransaction.KIND_EXPENSE,
            "Platform fee",
            "",
            "",
            "",
        )
        empty_other = _transaction(
            other,
            FinancialTransaction.KIND_EXPENSE,
            "Flour",
            "",
            "",
            "",
        )
        salary = _transaction(
            account,
            FinancialTransaction.KIND_EXPENSE,
            "Platform fee",
            "",
            "",
            FinancialTransaction.EXPENSE_SALARY,
        )
        income = _transaction(
            account,
            FinancialTransaction.KIND_INCOME,
            "Platform fee",
            "",
            "",
            "",
        )
        _rule(
            "Fees",
            FinancialTransaction.EXPENSE_FEES,
            1,
            FinancialTransactionRule.OPERATOR_OR,
            True,
            [(FinancialTransactionRuleCondition.FIELD_DESCRIPTION, "*fee")],
        )
        self.assertEqual(categorize_uncategorized_expenses(), 1)
        empty_fee.refresh_from_db()
        empty_other.refresh_from_db()
        salary.refresh_from_db()
        income.refresh_from_db()
        self.assertEqual(empty_fee.expense_type, FinancialTransaction.EXPENSE_FEES)
        self.assertEqual(empty_other.expense_type, "")
        self.assertEqual(salary.expense_type, FinancialTransaction.EXPENSE_SALARY)
        self.assertEqual(income.expense_type, "")


class ApplyExpenseRulesAdminTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(username="admin", password="password")
        self.client = Client()
        self.client.login(username="admin", password="password")

    def test_confirmation_page_applies_rules_to_the_whole_database(self):
        account = _account("Main", "GE00TB0000000000000001")
        matching = _transaction(
            account,
            FinancialTransaction.KIND_EXPENSE,
            "Platform fee",
            "",
            "",
            "",
        )
        kept = _transaction(
            account,
            FinancialTransaction.KIND_EXPENSE,
            "Platform fee",
            "",
            "",
            FinancialTransaction.EXPENSE_SALARY,
        )
        _rule(
            "Fees",
            FinancialTransaction.EXPENSE_FEES,
            1,
            FinancialTransactionRule.OPERATOR_OR,
            True,
            [(FinancialTransactionRuleCondition.FIELD_DESCRIPTION, "*fee")],
        )
        page = self.client.get("/admin/crm/financialtransaction/apply-rules/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Apply rules to the entire database")
        self.assertContains(page, "Existing categories stay unchanged.")
        response = self.client.post("/admin/crm/financialtransaction/apply-rules/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Categorized 1 transactions.")
        matching.refresh_from_db()
        kept.refresh_from_db()
        self.assertEqual(matching.expense_type, FinancialTransaction.EXPENSE_FEES)
        self.assertEqual(kept.expense_type, FinancialTransaction.EXPENSE_SALARY)

    def test_rule_requires_a_condition(self):
        response = self.client.post(
            "/admin/crm/financialtransactionrule/add/",
            {
                "name": "Fees",
                "expense_type": FinancialTransaction.EXPENSE_FEES,
                "priority": "1",
                "is_active": "on",
                "operator": FinancialTransactionRule.OPERATOR_OR,
                "conditions-TOTAL_FORMS": "0",
                "conditions-INITIAL_FORMS": "0",
                "conditions-MIN_NUM_FORMS": "0",
                "conditions-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add at least one condition.")
        self.assertEqual(FinancialTransactionRule.objects.count(), 0)

    def test_rule_saves_with_a_condition(self):
        response = self.client.post(
            "/admin/crm/financialtransactionrule/add/",
            {
                "name": "Fees",
                "expense_type": FinancialTransaction.EXPENSE_FEES,
                "priority": "1",
                "is_active": "on",
                "operator": FinancialTransactionRule.OPERATOR_AND,
                "conditions-TOTAL_FORMS": "1",
                "conditions-INITIAL_FORMS": "0",
                "conditions-MIN_NUM_FORMS": "0",
                "conditions-MAX_NUM_FORMS": "1000",
                "conditions-0-field": FinancialTransactionRuleCondition.FIELD_DESCRIPTION,
                "conditions-0-pattern": "*Fee*",
                "conditions-0-id": "",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        rule = FinancialTransactionRule.objects.get()
        self.assertEqual(rule.name, "Fees")
        condition = rule.conditions.get()
        self.assertEqual(condition.field, FinancialTransactionRuleCondition.FIELD_DESCRIPTION)
        self.assertEqual(condition.pattern, "*Fee*")
