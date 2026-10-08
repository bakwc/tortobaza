from crm.flowwow_statement import ACCOUNT_NAME
from crm.models import CrmOrder, FinancialTransaction


def sync_flowwow_order_links() -> None:
    transactions = FinancialTransaction.objects.filter(
        account__name=ACCOUNT_NAME,
        crm_orders__isnull=True,
    ).exclude(
        kind__in=[
            FinancialTransaction.KIND_WITHDRAWAL,
            FinancialTransaction.KIND_TRANSFER,
        ]
    )
    orders = {
        order.flowwow_order_id: order.pk
        for order in CrmOrder.objects.filter(
            is_paid=True,
            payment_type=CrmOrder.PAYMENT_FLOWWOW,
            deleted=False,
            flowwow_order_id__isnull=False,
        )
    }
    links = []
    for transaction in transactions:
        order_id = orders.get(_order_number(transaction.external_id))
        if order_id is None:
            continue
        links.append(
            FinancialTransaction.crm_orders.through(
                financialtransaction_id=transaction.pk,
                crmorder_id=order_id,
            )
        )
    if links:
        FinancialTransaction.crm_orders.through.objects.bulk_create(links)


def _order_number(external_id: str) -> int | None:
    segment, separator, _rest = external_id.partition("|")
    if separator == "" or not segment.isdigit():
        return None
    return int(segment)
