from django.conf import settings

from crm.models import CrmOrder
from orders.paypal import create_payment_link, gel_to_usd, nbg_usd_rate, update_payment_link


def assign_crm_payment_link(order: CrmOrder) -> None:
    remaining = order.total_price - order.prepayment
    amount_usd = gel_to_usd(remaining, nbg_usd_rate())
    if order.paypal_link_id:
        if order.paypal_amount_usd == amount_usd:
            return
        update_payment_link(order.paypal_link_id, order.pk, amount_usd, settings.SITE_URL)
        order.paypal_amount_usd = amount_usd
        return
    link_id, url = create_payment_link(order.pk, amount_usd, settings.SITE_URL)
    order.paypal_link_id = link_id
    order.paypal_payment_url = url
    order.paypal_amount_usd = amount_usd
