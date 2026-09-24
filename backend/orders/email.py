import threading

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils import translation
from django.utils.translation import gettext as _

from crm.models import CrmOrder
from orders.models import Order


def _format_money(amount) -> str:
    return f"{amount:.2f} ₾"


def _format_timeslot(order: Order) -> str:
    if order.timeslot_start is None or order.timeslot_end is None:
        return "—"
    start = timezone.localtime(order.timeslot_start)
    end = timezone.localtime(order.timeslot_end)
    date_part = start.strftime("%d.%m.%Y")
    time_part = f"{start.strftime('%H:%M')} – {end.strftime('%H:%M')}"
    return f"{date_part}, {time_part}"


def _format_address(order: Order) -> str:
    if order.fulfillment_type == Order.FULFILLMENT_PICKUP:
        if order.pickup_location is None:
            return "—"
        return f"{order.pickup_location.name}, {order.pickup_location.address}"
    addr = order.delivery_address
    if addr is None:
        return "—"
    parts = [addr.street]
    if addr.building:
        parts.append(addr.building)
    if addr.apartment:
        parts.append(f"{_('Apt.')} {addr.apartment}")
    line = ", ".join(parts)
    if addr.city:
        line = f"{line}, {addr.city}"
    if addr.notes:
        line = f"{line} ({addr.notes})"
    return line


def _format_items(order: Order) -> str:
    lines = []
    for item in order.items.all():
        line = f"• {item.product_name} × {item.quantity} — {_format_money(item.line_total)}"
        options = list(item.options.all())
        if options:
            opt_parts = [f"{o.group_name}: {o.option_name}" for o in options]
            line += f"\n  {', '.join(opt_parts)}"
        if item.comment:
            line += f"\n  {item.comment}"
        lines.append(line)
    return "\n".join(lines)


def _order_details(order: Order) -> str:
    fulfillment_labels = {
        Order.FULFILLMENT_DELIVERY: _("Delivery"),
        Order.FULFILLMENT_PICKUP: _("Pickup"),
    }
    payment_method_labels = {
        Order.PAYMENT_CARD: _("Card"),
        Order.PAYMENT_CASH: _("Cash"),
        Order.PAYMENT_BANK_TRANSFER: _("Bank transfer"),
    }
    location_label = (
        _("Address") if order.fulfillment_type == Order.FULFILLMENT_DELIVERY else _("Pickup point")
    )
    lines = [
        f"{_('Type:')} {fulfillment_labels[order.fulfillment_type]}",
        f"{location_label}: {_format_address(order)}",
        f"{_('Delivery time:')} {_format_timeslot(order)}",
        f"{_('Payment:')} {payment_method_labels[order.payment_method]}",
        f"{_('Total:')} {_format_money(order.total)}",
    ]
    if order.delivery_fee > 0:
        lines.append(f"{_('Delivery fee:')} {_format_money(order.delivery_fee)}")
    lines.extend(
        [
            "",
            f"{_('Items:')}",
            _format_items(order),
        ]
    )
    return "\n".join(lines)


def build_order_received_email(order: Order) -> tuple[str, str]:
    subject = _("Order #%(number)s received") % {"number": order.number}
    body = "\n".join(
        [
            _("Hello, %(name)s!") % {"name": order.customer_name},
            "",
            _(
                "We have received your order #%(number)s. It is not confirmed yet. "
                "It will be confirmed after card payment or by a manager."
            )
            % {"number": order.number},
            "",
            _order_details(order),
        ]
    )
    return subject, body


def build_order_confirmed_email(order: Order) -> tuple[str, str]:
    subject = _("Order #%(number)s confirmed") % {"number": order.number}
    body = "\n".join(
        [
            _("Hello, %(name)s!") % {"name": order.customer_name},
            "",
            _("Your order #%(number)s is confirmed.") % {"number": order.number},
            "",
            _order_details(order),
        ]
    )
    return subject, body


def _load_order(order_id: int) -> Order:
    return (
        Order.objects.select_related("pickup_location", "delivery_address")
        .prefetch_related("items__options")
        .get(pk=order_id)
    )


def _send_order_email(order: Order, subject: str, body: str) -> None:
    if order.environment == Order.ENV_DEV:
        return
    if not order.customer_email:
        return
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [order.customer_email])


def send_order_received_email(order_id: int) -> None:
    order = _load_order(order_id)
    with translation.override(order.locale):
        subject, body = build_order_received_email(order)
    _send_order_email(order, subject, body)


def send_order_confirmed_email(order_id: int) -> None:
    order = _load_order(order_id)
    with translation.override(order.locale):
        subject, body = build_order_confirmed_email(order)
    _send_order_email(order, subject, body)


def schedule_order_received_email(order_id: int) -> None:
    transaction.on_commit(
        lambda: threading.Thread(
            target=send_order_received_email,
            args=(order_id,),
            daemon=True,
        ).start()
    )


def schedule_order_confirmed_email(crm_order: CrmOrder, previous_status: str) -> None:
    if crm_order.website_order_id is None:
        return
    if previous_status != CrmOrder.STATUS_UNCONFIRMED or crm_order.status != CrmOrder.STATUS_NEW:
        return
    order_id = crm_order.website_order_id
    transaction.on_commit(
        lambda: threading.Thread(
            target=send_order_confirmed_email,
            args=(order_id,),
            daemon=True,
        ).start()
    )
