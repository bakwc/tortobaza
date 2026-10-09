import re
from dataclasses import dataclass

from django.utils import timezone

from crm.models import (
    FinancialTransaction,
    FinancialTransactionRule,
    FinancialTransactionRuleCondition,
)


@dataclass(frozen=True)
class ExpenseRuleCondition:
    field: str
    regex: re.Pattern[str]


@dataclass(frozen=True)
class ExpenseRule:
    expense_type: str
    operator: str
    conditions: tuple[ExpenseRuleCondition, ...]


def compile_wildcard(pattern: str) -> re.Pattern[str]:
    parts: list[str] = []
    for char in pattern:
        if char == "*":
            parts.append(".*")
        elif char == "?":
            parts.append(".")
        else:
            parts.append(re.escape(char))
    return re.compile("".join(parts), re.IGNORECASE)


def load_active_rules() -> list[ExpenseRule]:
    rules: list[ExpenseRule] = []
    queryset = (
        FinancialTransactionRule.objects.filter(is_active=True)
        .order_by("priority", "id")
        .prefetch_related("conditions")
    )
    for rule in queryset:
        rules.append(
            ExpenseRule(
                expense_type=rule.expense_type,
                operator=rule.operator,
                conditions=tuple(
                    ExpenseRuleCondition(
                        field=condition.field,
                        regex=compile_wildcard(condition.pattern),
                    )
                    for condition in rule.conditions.all()
                ),
            )
        )
    return rules


def condition_value(transaction: FinancialTransaction, field: str) -> str:
    if field == FinancialTransactionRuleCondition.FIELD_ACCOUNT_IBAN:
        return transaction.account.iban
    if field == FinancialTransactionRuleCondition.FIELD_COUNTERPARTY_IBAN:
        return transaction.counterparty_iban
    if field == FinancialTransactionRuleCondition.FIELD_COUNTERPARTY_NAME:
        return transaction.counterparty_name
    if field == FinancialTransactionRuleCondition.FIELD_DESCRIPTION:
        return transaction.description
    raise ValueError(field)


def rule_matches(rule: ExpenseRule, transaction: FinancialTransaction) -> bool:
    if len(rule.conditions) == 0:
        return False
    matches = [
        condition.regex.fullmatch(condition_value(transaction, condition.field)) is not None
        for condition in rule.conditions
    ]
    if rule.operator == FinancialTransactionRule.OPERATOR_AND:
        return all(matches)
    if rule.operator == FinancialTransactionRule.OPERATOR_OR:
        return any(matches)
    raise ValueError(rule.operator)


def matched_expense_type(transaction: FinancialTransaction, rules: list[ExpenseRule]) -> str:
    if transaction.kind != FinancialTransaction.KIND_EXPENSE:
        return ""
    for rule in rules:
        if rule_matches(rule, transaction):
            return rule.expense_type
    return ""


def assign_expense_types(transactions: list[FinancialTransaction]) -> None:
    rules = load_active_rules()
    for transaction in transactions:
        if transaction.expense_type != "":
            continue
        expense_type = matched_expense_type(transaction, rules)
        if expense_type != "":
            transaction.expense_type = expense_type


def categorize_uncategorized_expenses() -> int:
    rules = load_active_rules()
    categorized = 0
    pending: list[FinancialTransaction] = []
    now = timezone.now()
    queryset = FinancialTransaction.objects.filter(
        kind=FinancialTransaction.KIND_EXPENSE,
        expense_type="",
    ).select_related("account")
    for transaction in queryset.iterator(chunk_size=500):
        expense_type = matched_expense_type(transaction, rules)
        if expense_type == "":
            continue
        transaction.expense_type = expense_type
        transaction.updated_at = now
        pending.append(transaction)
        if len(pending) == 500:
            FinancialTransaction.objects.bulk_update(pending, ["expense_type", "updated_at"])
            categorized += len(pending)
            pending = []
    if pending:
        FinancialTransaction.objects.bulk_update(pending, ["expense_type", "updated_at"])
        categorized += len(pending)
    return categorized
