from collections.abc import Callable
from datetime import date
from decimal import Decimal

from crm.bog_order_links import _created_date, _estimated_payment_date
from crm.internal_transfers import normalize_iban
from crm.models import CrmOrder, FinancialTransaction
from crm.tbc_statement import BANK_NAME

WINDOW_DAYS = 2


def sync_tbc_order_links() -> None:
    transactions = [
        transaction
        for transaction in FinancialTransaction.objects.filter(
            kind=FinancialTransaction.KIND_INCOME,
            account__bank_name=BANK_NAME,
            crm_orders__isnull=True,
        )
        .select_related("account")
        .order_by("date", "pk")
        if normalize_iban(transaction.counterparty_iban) != normalize_iban(transaction.account.iban)
    ]
    orders = list(
        CrmOrder.objects.filter(
            is_paid=True,
            payment_type=CrmOrder.PAYMENT_TBC,
            deleted=False,
            financial_transactions__isnull=True,
        ).prefetch_related("events")
    )
    first, orders, transactions = _assign_one(orders, transactions, _estimated_payment_date)
    second, orders, transactions = _assign_one(orders, transactions, _created_date)
    third, orders, transactions = _assign_sums(orders, transactions, _estimated_payment_date)
    fourth, _orders, _transactions = _assign_sums(orders, transactions, _created_date)
    links = _pair_links(first + second) + _group_links(third + fourth)
    if links:
        FinancialTransaction.crm_orders.through.objects.bulk_create(links)


def _assign_one(
    orders: list[CrmOrder],
    transactions: list[FinancialTransaction],
    center: Callable[[CrmOrder], date],
) -> tuple[list[tuple[FinancialTransaction, CrmOrder]], list[CrmOrder], list[FinancialTransaction]]:
    preferences: list[tuple[int, FinancialTransaction, CrmOrder]] = []
    for transaction in transactions:
        candidates: list[tuple[int, int, CrmOrder]] = []
        for order in orders:
            if order.cake_price != transaction.amount:
                continue
            distance = abs((transaction.date - center(order)).days)
            if distance <= WINDOW_DAYS:
                candidates.append((distance, order.pk, order))
        if not candidates:
            continue
        candidates.sort(key=lambda item: (item[0], item[1]))
        distance, _order_pk, order = candidates[0]
        preferences.append((distance, transaction, order))
    grouped: dict[int, list[tuple[int, FinancialTransaction, CrmOrder]]] = {}
    for distance, transaction, order in preferences:
        grouped.setdefault(order.pk, []).append((distance, transaction, order))
    linked: list[tuple[FinancialTransaction, CrmOrder]] = []
    used_transactions: set[int] = set()
    used_orders: set[int] = set()
    for group in grouped.values():
        group.sort(key=lambda item: (item[0], item[1].date, item[1].pk))
        _distance, transaction, order = group[0]
        linked.append((transaction, order))
        used_transactions.add(transaction.pk)
        used_orders.add(order.pk)
    remaining_orders, remaining_transactions = _remaining(
        orders,
        transactions,
        used_orders,
        used_transactions,
    )
    return linked, remaining_orders, remaining_transactions


def _assign_sums(
    orders: list[CrmOrder],
    transactions: list[FinancialTransaction],
    center: Callable[[CrmOrder], date],
) -> tuple[
    list[tuple[list[FinancialTransaction], CrmOrder]],
    list[CrmOrder],
    list[FinancialTransaction],
]:
    by_sender: dict[str, list[FinancialTransaction]] = {}
    for transaction in transactions:
        by_sender.setdefault(normalize_iban(transaction.counterparty_iban), []).append(transaction)
    proposals: list[tuple[int, tuple[date, int], list[FinancialTransaction], CrmOrder]] = []
    for group in by_sender.values():
        if len(group) < 2:
            continue
        total = sum((transaction.amount for transaction in group), Decimal("0"))
        candidates: list[tuple[int, int, CrmOrder]] = []
        for order in orders:
            if order.cake_price != total:
                continue
            distances = [abs((transaction.date - center(order)).days) for transaction in group]
            if any(distance > WINDOW_DAYS for distance in distances):
                continue
            candidates.append((max(distances), order.pk, order))
        if not candidates:
            continue
        candidates.sort(key=lambda item: (item[0], item[1]))
        max_distance, _order_pk, order = candidates[0]
        earliest = min((transaction.date, transaction.pk) for transaction in group)
        proposals.append((max_distance, earliest, group, order))
    by_order: dict[int, list[tuple[int, tuple[date, int], list[FinancialTransaction], CrmOrder]]] = {}
    for proposal in proposals:
        by_order.setdefault(proposal[3].pk, []).append(proposal)
    linked: list[tuple[list[FinancialTransaction], CrmOrder]] = []
    used_transactions: set[int] = set()
    used_orders: set[int] = set()
    for proposals_for_order in by_order.values():
        proposals_for_order.sort(key=lambda item: (item[0], item[1]))
        _max_distance, _earliest, group, order = proposals_for_order[0]
        linked.append((group, order))
        used_orders.add(order.pk)
        for transaction in group:
            used_transactions.add(transaction.pk)
    remaining_orders, remaining_transactions = _remaining(
        orders,
        transactions,
        used_orders,
        used_transactions,
    )
    return linked, remaining_orders, remaining_transactions


def _remaining(
    orders: list[CrmOrder],
    transactions: list[FinancialTransaction],
    used_orders: set[int],
    used_transactions: set[int],
) -> tuple[list[CrmOrder], list[FinancialTransaction]]:
    return (
        [order for order in orders if order.pk not in used_orders],
        [transaction for transaction in transactions if transaction.pk not in used_transactions],
    )


def _pair_links(
    pairs: list[tuple[FinancialTransaction, CrmOrder]],
) -> list[FinancialTransaction.crm_orders.through]:
    return [
        FinancialTransaction.crm_orders.through(
            financialtransaction_id=transaction.pk,
            crmorder_id=order.pk,
        )
        for transaction, order in pairs
    ]


def _group_links(
    groups: list[tuple[list[FinancialTransaction], CrmOrder]],
) -> list[FinancialTransaction.crm_orders.through]:
    return [
        FinancialTransaction.crm_orders.through(
            financialtransaction_id=transaction.pk,
            crmorder_id=order.pk,
        )
        for group, order in groups
        for transaction in group
    ]
