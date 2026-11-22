from collections.abc import Callable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from crm.models import CrmOrder, ExchangeRateSnapshot, FinancialAccount, FinancialTransaction
from orders.models import PayPalPayment

ACCOUNT_NAME = "PayPal"
WINDOW_DAYS = 14
AMOUNT_TOLERANCE = Decimal("0.05")


def sync_paypal_order_links() -> None:
    account = _paypal_account()
    transactions = list(
        FinancialTransaction.objects.filter(
            account=account,
            kind=FinancialTransaction.KIND_INCOME,
            crm_orders__isnull=True,
        ).order_by("date", "pk")
    )
    orders = list(
        CrmOrder.objects.filter(
            is_paid=True,
            payment_type=CrmOrder.PAYMENT_PAYPAL,
            deleted=False,
            financial_transactions__isnull=True,
        )
    )
    captured, orders, transactions = _assign_captures(orders, transactions)
    snapshots = list(ExchangeRateSnapshot.objects.all())
    exact, orders, transactions = _assign(orders, transactions, _exact_amount)
    tolerated, _orders, _transactions = _assign(
        orders,
        transactions,
        lambda order, transaction: _amounts_near(order, transaction, snapshots),
    )
    pairs = captured + exact + tolerated
    links = _pair_links(pairs) + _fee_links(account, pairs)
    if links:
        FinancialTransaction.crm_orders.through.objects.bulk_create(links)


def _paypal_account() -> FinancialAccount:
    accounts = list(FinancialAccount.objects.filter(name=ACCOUNT_NAME))
    if len(accounts) == 0:
        raise FinancialAccount.DoesNotExist
    if len(accounts) > 1:
        raise ValueError("PayPal account matched more than once")
    return accounts[0]


def _assign_captures(
    orders: list[CrmOrder],
    transactions: list[FinancialTransaction],
) -> tuple[list[tuple[FinancialTransaction, CrmOrder]], list[CrmOrder], list[FinancialTransaction]]:
    capture_ids = [
        capture_id
        for transaction in transactions
        if (capture_id := _capture_id(transaction.external_id)) != ""
    ]
    payments = PayPalPayment.objects.filter(
        status=PayPalPayment.STATUS_COMPLETED,
        capture_id__in=capture_ids,
    )
    by_capture: dict[str, list[PayPalPayment]] = {}
    for payment in payments:
        if payment.capture_id == "":
            continue
        by_capture.setdefault(payment.capture_id, []).append(payment)
    website_ids = [payment.order_id for payment in payments]
    crm_by_website = {
        order.website_order_id: order
        for order in CrmOrder.objects.filter(
            website_order_id__in=website_ids,
            deleted=False,
            is_paid=True,
            financial_transactions__isnull=True,
        )
    }
    linked: list[tuple[FinancialTransaction, CrmOrder]] = []
    used_transactions: set[int] = set()
    used_orders: set[int] = set()
    for transaction in transactions:
        capture_id = _capture_id(transaction.external_id)
        if capture_id == "":
            continue
        matches = by_capture.get(capture_id, [])
        if len(matches) != 1:
            continue
        order = crm_by_website.get(matches[0].order_id)
        if order is None or order.pk in used_orders:
            continue
        linked.append((transaction, order))
        used_transactions.add(transaction.pk)
        used_orders.add(order.pk)
    remaining_orders = [order for order in orders if order.pk not in used_orders]
    remaining_transactions = [
        transaction for transaction in transactions if transaction.pk not in used_transactions
    ]
    return linked, remaining_orders, remaining_transactions


def _capture_id(external_id: str) -> str:
    if external_id == "":
        return ""
    return external_id.split("|", 1)[0]


def _exact_amount(order: CrmOrder, transaction: FinancialTransaction) -> bool:
    if order.paypal_amount_usd is None:
        return False
    return order.paypal_amount_usd == transaction.amount


def _amounts_near(
    order: CrmOrder,
    transaction: FinancialTransaction,
    snapshots: list[ExchangeRateSnapshot],
) -> bool:
    expected = _expected_usd(order, transaction.date, snapshots)
    return abs(transaction.amount - expected) <= expected * AMOUNT_TOLERANCE


def _expected_usd(
    order: CrmOrder,
    tx_date: date,
    snapshots: list[ExchangeRateSnapshot],
) -> Decimal:
    if order.paypal_amount_usd is not None:
        return order.paypal_amount_usd
    remaining = order.total_price - order.prepayment
    return (remaining / _usd_rate(snapshots, tx_date)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _usd_rate(snapshots: list[ExchangeRateSnapshot], tx_date: date) -> Decimal:
    if len(snapshots) == 0:
        raise ExchangeRateSnapshot.DoesNotExist
    closest = min(
        snapshots,
        key=lambda snapshot: (
            abs((snapshot.rates_date - tx_date).days),
            snapshot.rates_date.toordinal(),
            snapshot.pk,
        ),
    )
    return Decimal(closest.rates["USD"])


def _assign(
    orders: list[CrmOrder],
    transactions: list[FinancialTransaction],
    amounts_match: Callable[[CrmOrder, FinancialTransaction], bool],
) -> tuple[list[tuple[FinancialTransaction, CrmOrder]], list[CrmOrder], list[FinancialTransaction]]:
    preferences: list[tuple[int, FinancialTransaction, CrmOrder]] = []
    for transaction in transactions:
        candidates: list[tuple[int, CrmOrder]] = []
        for order in orders:
            if _distance(order, transaction.date) > WINDOW_DAYS:
                continue
            if not amounts_match(order, transaction):
                continue
            candidates.append((_distance(order, transaction.date), order))
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
        _distance_days, transaction, order = group[0]
        linked.append((transaction, order))
        used_transactions.add(transaction.pk)
        used_orders.add(order.pk)
    remaining_orders = [order for order in orders if order.pk not in used_orders]
    remaining_transactions = [
        transaction for transaction in transactions if transaction.pk not in used_transactions
    ]
    return linked, remaining_orders, remaining_transactions


def _distance(order: CrmOrder, tx_date: date) -> int:
    anchors = [order.date, timezone.localtime(order.created_at).date()]
    if order.payment_date is not None:
        anchors.append(order.payment_date)
    return min(abs((tx_date - anchor).days) for anchor in anchors)


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


def _fee_links(
    account: FinancialAccount,
    pairs: list[tuple[FinancialTransaction, CrmOrder]],
) -> list[FinancialTransaction.crm_orders.through]:
    fee_ids = [f"{transaction.external_id}|fee" for transaction, _order in pairs if transaction.external_id != ""]
    grouped: dict[str, list[FinancialTransaction]] = {}
    for fee in FinancialTransaction.objects.filter(
        account=account,
        external_id__in=fee_ids,
        crm_orders__isnull=True,
    ):
        grouped.setdefault(fee.external_id, []).append(fee)
    links = []
    for transaction, order in pairs:
        if transaction.external_id == "":
            continue
        fee_id = f"{transaction.external_id}|fee"
        fees = grouped.get(fee_id, [])
        if len(fees) != 1:
            continue
        del grouped[fee_id]
        links.append(
            FinancialTransaction.crm_orders.through(
                financialtransaction_id=fees[0].pk,
                crmorder_id=order.pk,
            )
        )
    return links
