from django.db import transaction

from crm.bog_order_links import ACCOUNT_NAME as BOG_ACCOUNT_NAME
from crm.flowwow_statement import ACCOUNT_NAME as FLOWWOW_ACCOUNT_NAME
from crm.models import FinancialTransaction

WINDOW_DAYS = 14


def sync_flowwow_bog_transfers() -> None:
    withdrawals = list(
        FinancialTransaction.objects.filter(
            account__name=FLOWWOW_ACCOUNT_NAME,
            kind=FinancialTransaction.KIND_WITHDRAWAL,
            amount__lt=0,
            matched_transaction__isnull=True,
        )
    )
    incomes = list(
        FinancialTransaction.objects.filter(
            account__name=BOG_ACCOUNT_NAME,
            kind=FinancialTransaction.KIND_INCOME,
            amount__gt=0,
            matched_transaction__isnull=True,
        )
    )
    withdrawal_matches: dict[int, list[FinancialTransaction]] = {}
    income_matches: dict[int, list[FinancialTransaction]] = {}
    for withdrawal in withdrawals:
        for income in incomes:
            if income.amount != -withdrawal.amount:
                continue
            delay = (income.date - withdrawal.date).days
            if delay < 0 or delay > WINDOW_DAYS:
                continue
            withdrawal_matches.setdefault(withdrawal.pk, []).append(income)
            income_matches.setdefault(income.pk, []).append(withdrawal)
    pairs: list[tuple[FinancialTransaction, FinancialTransaction]] = []
    for withdrawal in withdrawals:
        matches = withdrawal_matches.get(withdrawal.pk, [])
        if len(matches) != 1:
            continue
        income = matches[0]
        if len(income_matches[income.pk]) != 1:
            continue
        pairs.append((withdrawal, income))
    if not pairs:
        return
    with transaction.atomic():
        for withdrawal, income in pairs:
            withdrawal.kind = FinancialTransaction.KIND_TRANSFER
            withdrawal.matched_transaction = income
            income.kind = FinancialTransaction.KIND_TRANSFER
            income.matched_transaction = withdrawal
            withdrawal.save(update_fields=["kind", "matched_transaction", "updated_at"])
            income.save(update_fields=["kind", "matched_transaction", "updated_at"])
