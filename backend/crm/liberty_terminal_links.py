import re
from datetime import date, timedelta
from decimal import Decimal
from itertools import combinations

from crm.liberty_statement import TERMINAL_PREFIX
from crm.models import CrmOrder, FinancialTransaction

MAX_COMMISSION = Decimal("0.10")
_SALES_DATE = re.compile(r"(\d{1,2})\.(\d{2})\.(\d{4})")


def sync_liberty_terminal_order_links() -> None:
    pending: list[tuple[date, FinancialTransaction]] = []
    for transaction in FinancialTransaction.objects.filter(
        kind=FinancialTransaction.KIND_INCOME,
        income_type=FinancialTransaction.INCOME_TERMINAL,
        description__startswith=TERMINAL_PREFIX,
        crm_orders__isnull=True,
    ):
        sales_date = _sales_date(transaction.description)
        if sales_date is None:
            continue
        pending.append((sales_date, transaction))
    pending.sort(key=lambda item: (item[0], item[1].pk))
    available = {
        order.pk: order
        for order in CrmOrder.objects.filter(
            is_paid=True,
            payment_type=CrmOrder.PAYMENT_TERMINAL,
            deleted=False,
            financial_transactions__isnull=True,
        )
    }
    links = []
    for sales_date, transaction in pending:
        candidates = [
            order
            for order in available.values()
            if sales_date - timedelta(days=1) <= order.date <= sales_date
        ]
        matched = _unique_subset(candidates, transaction.amount)
        if matched is None:
            continue
        for order in matched:
            links.append(
                FinancialTransaction.crm_orders.through(
                    financialtransaction_id=transaction.pk,
                    crmorder_id=order.pk,
                )
            )
            del available[order.pk]
    if links:
        FinancialTransaction.crm_orders.through.objects.bulk_create(links)


def _sales_date(description: str) -> date | None:
    match = _SALES_DATE.search(description)
    if match is None:
        return None
    day, month, year = (int(part) for part in match.groups())
    return date(year, month, day)


def _unique_subset(orders: list[CrmOrder], amount: Decimal) -> list[CrmOrder] | None:
    matched: list[CrmOrder] | None = None
    for size in range(1, len(orders) + 1):
        for subset in combinations(orders, size):
            gross = sum((order.cake_price for order in subset), Decimal("0"))
            if gross <= amount:
                continue
            if (gross - amount) / gross > MAX_COMMISSION:
                continue
            if matched is not None:
                return None
            matched = list(subset)
    return matched
