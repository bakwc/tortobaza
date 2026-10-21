from collections.abc import Callable
from datetime import date
from decimal import Decimal

from django.utils import timezone

from crm.internal_transfers import BOG_BANK_NAME
from crm.models import CrmOrder, FinancialTransaction

ACCOUNT_NAME = "BOG business GEL"
WINDOW_DAYS = 2
AMOUNT_TOLERANCE = Decimal("0.03")
_PLATFORM_MARKERS = ("wolt", "volt jorjia", "udora", "g-1002221")


def sync_bog_order_links() -> None:
    transactions = [
        transaction
        for transaction in FinancialTransaction.objects.filter(
            kind=FinancialTransaction.KIND_INCOME,
            account__bank_name=BOG_BANK_NAME,
            crm_orders__isnull=True,
        ).order_by("date", "pk")
        if not _is_platform(transaction)
    ]
    orders = list(
        CrmOrder.objects.filter(
            is_paid=True,
            payment_type=CrmOrder.PAYMENT_BOG,
            deleted=False,
            financial_transactions__isnull=True,
        ).prefetch_related("events")
    )
    exact_payment, orders, transactions = _assign(orders, transactions, _estimated_payment_date, True)
    exact_created, orders, transactions = _assign(orders, transactions, _created_date, True)
    near_payment, orders, transactions = _assign(orders, transactions, _estimated_payment_date, False)
    near_created, _orders, _transactions = _assign(orders, transactions, _created_date, False)
    links = [
        FinancialTransaction.crm_orders.through(
            financialtransaction_id=transaction.pk,
            crmorder_id=order.pk,
        )
        for transaction, order in exact_payment + exact_created + near_payment + near_created
    ]
    if links:
        FinancialTransaction.crm_orders.through.objects.bulk_create(links)


def _is_platform(transaction: FinancialTransaction) -> bool:
    blob = f"{transaction.counterparty_name}\n{transaction.description}".lower()
    return any(marker in blob for marker in _PLATFORM_MARKERS)


def _estimated_payment_date(order: CrmOrder) -> date:
    if order.payment_date is not None:
        return order.payment_date
    paid_on = _history_paid_date(order)
    if paid_on is not None:
        return paid_on
    return order.date


def _history_paid_date(order: CrmOrder) -> date | None:
    for event in order.events.all():
        if event.changes.get("is_paid") == {"old": False, "new": True}:
            return timezone.localtime(event.created_at).date()
    return None


def _created_date(order: CrmOrder) -> date:
    return timezone.localtime(order.created_at).date()


def _amounts_match(order: CrmOrder, transaction: FinancialTransaction, exact: bool) -> bool:
    if exact:
        return order.total_price == transaction.amount
    return abs(order.total_price - transaction.amount) <= order.total_price * AMOUNT_TOLERANCE


def _assign(
    orders: list[CrmOrder],
    transactions: list[FinancialTransaction],
    center: Callable[[CrmOrder], date],
    exact: bool,
) -> tuple[list[tuple[FinancialTransaction, CrmOrder]], list[CrmOrder], list[FinancialTransaction]]:
    preferences: list[tuple[int, FinancialTransaction, CrmOrder]] = []
    for transaction in transactions:
        candidates: list[tuple[int, CrmOrder]] = []
        for order in orders:
            if not _amounts_match(order, transaction, exact):
                continue
            distance = abs((transaction.date - center(order)).days)
            if distance <= WINDOW_DAYS:
                candidates.append((distance, order))
        if not candidates:
            continue
        best_distance = min(distance for distance, _order in candidates)
        closest = [order for distance, order in candidates if distance == best_distance]
        if len(closest) != 1:
            continue
        preferences.append((best_distance, transaction, closest[0]))
    grouped: dict[int, list[tuple[int, FinancialTransaction, CrmOrder]]] = {}
    for distance, transaction, order in preferences:
        grouped.setdefault(order.pk, []).append((distance, transaction, order))
    linked: list[tuple[FinancialTransaction, CrmOrder]] = []
    used_transactions: set[int] = set()
    used_orders: set[int] = set()
    for group in grouped.values():
        group.sort(key=lambda item: (item[0], item[1].date, item[1].pk))
        if len(group) > 1 and group[0][0] == group[1][0]:
            continue
        _distance, transaction, order = group[0]
        linked.append((transaction, order))
        used_transactions.add(transaction.pk)
        used_orders.add(order.pk)
    remaining_orders = [order for order in orders if order.pk not in used_orders]
    remaining_transactions = [
        transaction for transaction in transactions if transaction.pk not in used_transactions
    ]
    return linked, remaining_orders, remaining_transactions
