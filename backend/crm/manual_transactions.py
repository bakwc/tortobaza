from rest_framework.exceptions import ValidationError

from crm.models import FinancialTransaction

PAIR_NONE = "none"
PAIR_LINK = "link"
PAIR_CREATE = "create"


def create_manual_transaction(data: dict) -> FinancialTransaction:
    tx = FinancialTransaction(
        account_id=data["account_id"],
        date=data["date"],
        amount=data["amount"],
        kind=data["kind"],
        income_type=data["income_type"],
        expense_type=data["expense_type"],
        counterparty_name=data["counterparty_name"],
        counterparty_iban=data["counterparty_iban"],
        description=data["description"],
    )
    tx.save()
    apply_transfer_pair(tx, data)
    return tx


def delete_manual_transaction(tx: FinancialTransaction) -> None:
    unlink(tx)
    tx.delete()


def update_manual_transaction(tx: FinancialTransaction, data: dict) -> FinancialTransaction:
    tx.account_id = data["account_id"]
    tx.date = data["date"]
    tx.amount = data["amount"]
    tx.kind = data["kind"]
    tx.income_type = data["income_type"]
    tx.expense_type = data["expense_type"]
    tx.counterparty_name = data["counterparty_name"]
    tx.counterparty_iban = data["counterparty_iban"]
    tx.description = data["description"]
    tx.save()
    apply_transfer_pair(tx, data)
    return tx


def apply_transfer_pair(tx: FinancialTransaction, data: dict) -> None:
    pair = data["transfer_pair"]
    if tx.kind != FinancialTransaction.KIND_TRANSFER or pair == PAIR_NONE:
        unlink(tx)
        return
    if pair == PAIR_LINK:
        target = FinancialTransaction.objects.get(pk=data["matched_transaction_id"])
        if target.pk == tx.pk:
            raise ValidationError({"matched_transaction_id": "A transaction cannot be linked to itself."})
        link(tx, target)
        return
    counterpart = data["counterpart"]
    other = FinancialTransaction(
        account_id=counterpart["account_id"],
        date=counterpart["date"],
        amount=counterpart["amount"],
        kind=FinancialTransaction.KIND_TRANSFER,
        income_type="",
        expense_type="",
        counterparty_name="",
        counterparty_iban="",
        description=tx.description,
    )
    other.save()
    link(tx, other)


def unlink(tx: FinancialTransaction) -> None:
    other = tx.matched_transaction
    if tx.matched_transaction_id is not None:
        tx.matched_transaction = None
        tx.save(update_fields=["matched_transaction", "updated_at"])
    if other is not None and other.matched_transaction_id == tx.pk:
        other.matched_transaction = None
        other.save(update_fields=["matched_transaction", "updated_at"])
    for partner in FinancialTransaction.objects.filter(matched_transaction_id=tx.pk):
        partner.matched_transaction = None
        partner.save(update_fields=["matched_transaction", "updated_at"])


def link(tx: FinancialTransaction, target: FinancialTransaction) -> None:
    unlink(tx)
    unlink(target)
    target.kind = FinancialTransaction.KIND_TRANSFER
    target.income_type = ""
    target.expense_type = ""
    target.matched_transaction = tx
    tx.matched_transaction = target
    target.save(
        update_fields=["kind", "income_type", "expense_type", "matched_transaction", "updated_at"]
    )
    tx.save(update_fields=["matched_transaction", "updated_at"])
