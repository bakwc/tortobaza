import re
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from crm.liberty_statement import ONLINE_PREFIX
from crm.models import CrmOrder, FinancialTransaction
from orders.models import LibertyPayment

MAX_COMMISSION = Decimal("0.10")
_TB = ZoneInfo("Asia/Tbilisi")
_PAYMENT_DETAILS = re.compile(
    r"(\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2}):(\d{2}).*?GEL (\d+\.\d{2})"
)


def sync_liberty_online_order_links() -> None:
    pending: list[tuple[datetime, Decimal, FinancialTransaction]] = []
    for transaction in FinancialTransaction.objects.filter(
        kind=FinancialTransaction.KIND_INCOME,
        income_type=FinancialTransaction.INCOME_ONLINE,
        description__startswith=ONLINE_PREFIX,
        crm_orders__isnull=True,
    ):
        parsed = _payment_details(transaction.description)
        if parsed is None:
            continue
        authorized_at, gross = parsed
        if gross <= transaction.amount:
            continue
        if (gross - transaction.amount) / gross > MAX_COMMISSION:
            continue
        pending.append((authorized_at, gross, transaction))
    pending.sort(key=lambda item: (item[0], item[2].pk))
    available = {
        order.pk: order
        for order in CrmOrder.objects.filter(
            is_paid=True,
            payment_type=CrmOrder.PAYMENT_ONLINE,
            deleted=False,
            financial_transactions__isnull=True,
            website_order__isnull=False,
        )
    }
    payments = list(
        LibertyPayment.objects.filter(
            status=LibertyPayment.STATUS_COMPLETED,
            testmode=False,
            order__crm_order__pk__in=available,
        ).select_related("order__crm_order")
    )
    links = []
    for authorized_at, gross, transaction in pending:
        amount_tetri = int(gross * 100)
        matched: LibertyPayment | None = None
        for payment in payments:
            if payment.amount_tetri != amount_tetri:
                continue
            order = payment.order.crm_order
            if order.pk not in available:
                continue
            created = payment.created_at.astimezone(_TB)
            updated = payment.updated_at.astimezone(_TB)
            if not created <= authorized_at <= updated:
                continue
            if matched is not None:
                matched = None
                break
            matched = payment
        if matched is None:
            continue
        order = matched.order.crm_order
        links.append(
            FinancialTransaction.crm_orders.through(
                financialtransaction_id=transaction.pk,
                crmorder_id=order.pk,
            )
        )
        del available[order.pk]
    if links:
        FinancialTransaction.crm_orders.through.objects.bulk_create(links)


def _payment_details(description: str) -> tuple[datetime, Decimal] | None:
    match = _PAYMENT_DETAILS.search(description)
    if match is None:
        return None
    day, month, year, hour, minute, second, gel = match.groups()
    authorized_at = datetime(
        int(year),
        int(month),
        int(day),
        int(hour),
        int(minute),
        int(second),
        tzinfo=_TB,
    )
    return authorized_at, Decimal(gel)
