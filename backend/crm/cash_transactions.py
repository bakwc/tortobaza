from django.utils import timezone

from crm.models import CrmOrder, FinancialAccount, FinancialTransaction


def sync_cash_paid_order_transactions() -> None:
    orders = list(
        CrmOrder.objects.filter(
            is_paid=True,
            payment_type=CrmOrder.PAYMENT_CASH,
            deleted=False,
            financial_transactions__isnull=True,
        ).prefetch_related("events")
    )
    if not orders:
        return
    account = (
        FinancialAccount.objects.filter(kind=FinancialAccount.KIND_CASH)
        .order_by("pk")
        .first()
    )
    if account is None:
        raise FinancialAccount.DoesNotExist
    FinancialTransaction.objects.bulk_create(
        [
            FinancialTransaction(
                account=account,
                date=_transaction_date(order),
                amount=order.cake_price,
                kind=FinancialTransaction.KIND_INCOME,
                income_type=FinancialTransaction.INCOME_CASH,
                crm_order=order,
            )
            for order in orders
        ]
    )


def _transaction_date(order: CrmOrder):
    for event in order.events.all():
        if event.changes.get("is_paid") == {"old": False, "new": True}:
            return timezone.localtime(event.created_at).date()
    return order.date
