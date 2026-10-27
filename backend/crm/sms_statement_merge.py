from datetime import date
from decimal import Decimal
from typing import Protocol

from crm.models import CardSmsMessage, FinancialTransaction
from crm.transaction_rules import assign_expense_types
from tortobaza.finance_db import current_finance_db

STATEMENT_UPDATE_FIELDS = [
    "date",
    "amount",
    "kind",
    "income_type",
    "counterparty_name",
    "counterparty_iban",
    "description",
    "external_id",
    "expense_type",
]


class StatementRow(Protocol):
    date: date
    amount: Decimal
    kind: str
    income_type: str
    counterparty_name: str
    counterparty_iban: str
    description: str
    external_id: str


def absorb_open_sms(
    pending: list[tuple[int, StatementRow]],
) -> dict[int, FinancialTransaction]:
    if len(pending) == 0:
        return {}
    account_ids = [account_id for account_id, _row in pending]
    assigned = _assign_sms(pending, _open_sms_by_account(account_ids))
    updated = list(assigned.values())
    for index, tx in assigned.items():
        _copy_statement(tx, pending[index][1])
    assign_expense_types(updated)
    return assigned


def _open_sms_by_account(account_ids: list[int]) -> dict[int, list[FinancialTransaction]]:
    alias = current_finance_db()
    links = CardSmsMessage.objects.filter(
        status=CardSmsMessage.STATUS_INSERTED,
        finance_db=alias,
        transaction_id__isnull=False,
    )
    message_by_tx = {link.transaction_id: link.message_id for link in links}
    grouped: dict[int, list[FinancialTransaction]] = {}
    if len(message_by_tx) == 0:
        return grouped
    queryset = FinancialTransaction.objects.filter(
        pk__in=message_by_tx,
        account_id__in=account_ids,
    ).select_related("account")
    for tx in queryset:
        if tx.external_id != message_by_tx[tx.pk]:
            continue
        grouped.setdefault(tx.account_id, []).append(tx)
    return grouped


def _assign_sms(
    pending: list[tuple[int, StatementRow]],
    sms_by_account: dict[int, list[FinancialTransaction]],
) -> dict[int, FinancialTransaction]:
    pairs: list[tuple[int, int, int, FinancialTransaction]] = []
    for index, (account_id, row) in enumerate(pending):
        for tx in sms_by_account.get(account_id, []):
            if tx.amount != row.amount:
                continue
            delta = abs((row.date - tx.date).days)
            if delta > 1:
                continue
            pairs.append((delta, tx.pk, index, tx))
    pairs.sort(key=lambda item: (item[0], item[1], item[2]))
    used_transactions: set[int] = set()
    used_rows: set[int] = set()
    assigned: dict[int, FinancialTransaction] = {}
    for _delta, tx_pk, index, tx in pairs:
        if tx_pk in used_transactions or index in used_rows:
            continue
        used_transactions.add(tx_pk)
        used_rows.add(index)
        assigned[index] = tx
    return assigned


def _copy_statement(tx: FinancialTransaction, row: StatementRow) -> None:
    tx.date = row.date
    tx.amount = row.amount
    tx.kind = row.kind
    tx.income_type = row.income_type
    tx.counterparty_name = row.counterparty_name
    tx.counterparty_iban = row.counterparty_iban
    tx.description = row.description
    tx.external_id = row.external_id
