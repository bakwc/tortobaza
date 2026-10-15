from decimal import Decimal

from django.db import transaction

from crm.models import FinancialAccount, FinancialTransaction

BOG_BANK_NAME = "Bank Of Georgia"
TBC_BANK_NAME = "TBC"
ATM_CASH_PREFIX = "ATM CASH"
ATM_FEE_DESCRIPTION = "Комиссия за снятие"
WINDOW_DAYS = 3


def normalize_iban(value: str) -> str:
    return value.upper().replace(" ", "")[:22]


def sync_internal_transfers() -> None:
    by_key = bank_accounts_by_iban()
    candidates = [
        tx
        for tx in FinancialTransaction.objects.filter(
            account__kind=FinancialAccount.KIND_BANK,
        ).select_related("account")
        if counterparty_account(tx, by_key) is not None
    ]
    fee_ids = bog_fee_ids(candidates)
    with transaction.atomic():
        mark_transfers(candidates, fee_ids)
        pair_transfers(by_key)
        pair_tbc_atm_withdrawals()


def bank_accounts_by_iban() -> dict[tuple[str, str], FinancialAccount]:
    by_key: dict[tuple[str, str], FinancialAccount] = {}
    for account in FinancialAccount.objects.filter(kind=FinancialAccount.KIND_BANK):
        key = (normalize_iban(account.iban), account.currency)
        if key in by_key:
            raise ValueError(
                f"Bank accounts {by_key[key].name} and {account.name} share IBAN {key[0]} and currency {key[1]}"
            )
        by_key[key] = account
    return by_key


def counterparty_account(
    tx: FinancialTransaction,
    by_key: dict[tuple[str, str], FinancialAccount],
) -> FinancialAccount | None:
    account = by_key.get((normalize_iban(tx.counterparty_iban), tx.account.currency))
    if account is None or account.pk == tx.account_id:
        return None
    return account


def bog_fee_ids(candidates: list[FinancialTransaction]) -> set[int]:
    fee_ids: set[int] = set()
    for tx in candidates:
        if tx.account.bank_name != BOG_BANK_NAME or tx.amount >= 0:
            continue
        for other in candidates:
            if other.pk == tx.pk or other.account_id != tx.account_id:
                continue
            if other.date != tx.date or other.counterparty_iban != tx.counterparty_iban:
                continue
            if other.description != tx.description:
                continue
            if external_id_is_next(tx.external_id, other.external_id):
                fee_ids.add(tx.pk)
                break
    return fee_ids


def external_id_is_next(fee_external_id: str, main_external_id: str) -> bool:
    if not fee_external_id.isdigit() or not main_external_id.isdigit():
        return False
    return int(fee_external_id) == int(main_external_id) + 1


def mark_transfers(candidates: list[FinancialTransaction], fee_ids: set[int]) -> None:
    for tx in candidates:
        if tx.pk in fee_ids:
            if (
                tx.kind == FinancialTransaction.KIND_EXPENSE
                and tx.expense_type == FinancialTransaction.EXPENSE_FEES
            ):
                continue
            tx.kind = FinancialTransaction.KIND_EXPENSE
            tx.expense_type = FinancialTransaction.EXPENSE_FEES
            tx.save(update_fields=["kind", "expense_type", "updated_at"])
            continue
        if tx.expense_type == FinancialTransaction.EXPENSE_FEES:
            continue
        if tx.kind not in (FinancialTransaction.KIND_INCOME, FinancialTransaction.KIND_EXPENSE):
            continue
        tx.kind = FinancialTransaction.KIND_TRANSFER
        tx.save(update_fields=["kind", "updated_at"])


def pair_transfers(by_key: dict[tuple[str, str], FinancialAccount]) -> None:
    transfers = list(
        FinancialTransaction.objects.filter(
            account__kind=FinancialAccount.KIND_BANK,
            kind=FinancialTransaction.KIND_TRANSFER,
            matched_transaction__isnull=True,
        ).select_related("account")
    )
    outgoing_matches: dict[int, list[FinancialTransaction]] = {}
    incoming_matches: dict[int, list[FinancialTransaction]] = {}
    resolved: dict[int, FinancialAccount] = {}
    for tx in transfers:
        account = counterparty_account(tx, by_key)
        if account is None or tx.amount == 0:
            continue
        resolved[tx.pk] = account
    for outgoing in transfers:
        destination = resolved.get(outgoing.pk)
        if destination is None or outgoing.amount >= 0:
            continue
        for incoming in transfers:
            source = resolved.get(incoming.pk)
            if source is None or incoming.amount <= 0:
                continue
            if incoming.account_id != destination.pk or source.pk != outgoing.account_id:
                continue
            if incoming.amount != -outgoing.amount:
                continue
            delay = (incoming.date - outgoing.date).days
            if delay < 0 or delay > WINDOW_DAYS:
                continue
            outgoing_matches.setdefault(outgoing.pk, []).append(incoming)
            incoming_matches.setdefault(incoming.pk, []).append(outgoing)
    pairs: list[tuple[FinancialTransaction, FinancialTransaction]] = []
    for outgoing in transfers:
        matches = outgoing_matches.get(outgoing.pk, [])
        if len(matches) != 1:
            continue
        incoming = matches[0]
        if len(incoming_matches[incoming.pk]) != 1:
            continue
        pairs.append((outgoing, incoming))
    for outgoing, incoming in pairs:
        outgoing.matched_transaction = incoming
        incoming.matched_transaction = outgoing
        outgoing.save(update_fields=["matched_transaction", "updated_at"])
        incoming.save(update_fields=["matched_transaction", "updated_at"])


def pair_tbc_atm_withdrawals() -> None:
    withdrawals = list(
        FinancialTransaction.objects.filter(
            account__bank_name=TBC_BANK_NAME,
            account__kind=FinancialAccount.KIND_BANK,
            amount__lt=0,
            matched_transaction__isnull=True,
            description__startswith=ATM_CASH_PREFIX,
        ).select_related("account")
    )
    if not withdrawals:
        return
    cash_transfers = list(
        FinancialTransaction.objects.filter(
            account__kind=FinancialAccount.KIND_CASH,
            kind=FinancialTransaction.KIND_TRANSFER,
            matched_transaction__isnull=True,
            amount__gt=0,
        ).select_related("account")
    )
    assigned = assign_atm_cash(withdrawals, cash_transfers)
    pending = [tx for tx in withdrawals if tx.pk not in assigned]
    for tx in withdrawals:
        incoming = assigned.get(tx.pk)
        if incoming is None:
            continue
        link_atm_withdrawal(tx, incoming)
        create_atm_withdrawal_fee(tx, incoming)
    if not pending:
        return
    cash = (
        FinancialAccount.objects.filter(kind=FinancialAccount.KIND_CASH)
        .order_by("pk")
        .first()
    )
    if cash is None:
        raise FinancialAccount.DoesNotExist
    for tx in pending:
        incoming = FinancialTransaction.objects.create(
            account=cash,
            date=tx.date,
            amount=-tx.amount,
            kind=FinancialTransaction.KIND_TRANSFER,
            description=tx.description,
            external_id=tx.external_id,
        )
        link_atm_withdrawal(tx, incoming)


def link_atm_withdrawal(
    withdrawal: FinancialTransaction,
    incoming: FinancialTransaction,
) -> None:
    withdrawal.kind = FinancialTransaction.KIND_TRANSFER
    withdrawal.matched_transaction = incoming
    incoming.matched_transaction = withdrawal
    withdrawal.save(update_fields=["kind", "matched_transaction", "updated_at"])
    incoming.save(update_fields=["matched_transaction", "updated_at"])


def assign_atm_cash(
    withdrawals: list[FinancialTransaction],
    cash_transfers: list[FinancialTransaction],
) -> dict[int, FinancialTransaction]:
    cash_by_id = {tx.pk: tx for tx in cash_transfers}
    candidates: list[tuple[Decimal, int, int, int]] = []
    for withdrawal in withdrawals:
        bank_amount = -withdrawal.amount
        for cash_tx in cash_transfers:
            if cash_tx.account.currency != withdrawal.account.currency:
                continue
            delay = (cash_tx.date - withdrawal.date).days
            if delay < 0 or delay > WINDOW_DAYS:
                continue
            diff = abs(bank_amount - cash_tx.amount)
            if diff * 100 > bank_amount:
                continue
            candidates.append((diff, delay, cash_tx.pk, withdrawal.pk))
    candidates.sort()
    used_cash: set[int] = set()
    used_withdrawals: set[int] = set()
    assigned: dict[int, FinancialTransaction] = {}
    for _diff, _delay, cash_pk, withdrawal_pk in candidates:
        if cash_pk in used_cash or withdrawal_pk in used_withdrawals:
            continue
        used_cash.add(cash_pk)
        used_withdrawals.add(withdrawal_pk)
        assigned[withdrawal_pk] = cash_by_id[cash_pk]
    return assigned


def create_atm_withdrawal_fee(
    withdrawal: FinancialTransaction,
    incoming: FinancialTransaction,
) -> None:
    fee_amount = incoming.amount + withdrawal.amount
    if fee_amount >= 0:
        return
    FinancialTransaction.objects.create(
        account=incoming.account,
        date=withdrawal.date,
        amount=fee_amount,
        kind=FinancialTransaction.KIND_EXPENSE,
        expense_type=FinancialTransaction.EXPENSE_FEES,
        description=ATM_FEE_DESCRIPTION,
        external_id=f"atm-fee:{withdrawal.pk}",
    )
