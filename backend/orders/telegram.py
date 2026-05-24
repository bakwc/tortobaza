import html
import json
import urllib.request

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _

from orders.models import Order


def _esc(value: str) -> str:
    return html.escape(value, quote=False)


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
        line = f"• {_esc(item.product_name)} × {item.quantity} — {_format_money(item.line_total)}"
        options = list(item.options.all())
        if options:
            opt_parts = [f"{_esc(o.group_name)}: {_esc(o.option_name)}" for o in options]
            line += f"\n  {', '.join(opt_parts)}"
        if item.comment:
            line += f"\n  {_esc(item.comment)}"
        lines.append(line)
    return "\n".join(lines)


def build_order_notification_text(order: Order) -> str:
    fulfillment_labels = {
        Order.FULFILLMENT_DELIVERY: _("Delivery"),
        Order.FULFILLMENT_PICKUP: _("Pickup"),
    }
    payment_method_labels = {
        Order.PAYMENT_CARD: _("Card"),
        Order.PAYMENT_CASH: _("Cash"),
        Order.PAYMENT_BANK_TRANSFER: _("Bank transfer"),
    }

    admin_url = f"{settings.SITE_URL}/admin/orders/order/{order.pk}/change/"
    fulfillment = fulfillment_labels[order.fulfillment_type]
    payment = payment_method_labels[order.payment_method]
    location_label = (
        _("Address") if order.fulfillment_type == Order.FULFILLMENT_DELIVERY else _("Pickup point")
    )

    lines = [
        _("🆕 <b>New order #%(number)s</b>") % {"number": _esc(order.number)},
        "",
        f"<b>{_('Customer:')}</b> {_esc(order.customer_name)}",
        f"<b>{_('Phone:')}</b> {_esc(order.customer_phone)}",
    ]
    if order.customer_email:
        lines.append(f"<b>{_('Email:')}</b> {_esc(order.customer_email)}")
    if order.customer_instagram:
        lines.append(f"<b>{_('Instagram:')}</b> {_esc(order.customer_instagram)}")
    if order.customer_telegram:
        lines.append(f"<b>{_('Telegram:')}</b> {_esc(order.customer_telegram)}")
    lines.extend(
        [
            f"<b>{_('Type:')}</b> {fulfillment}",
            f"<b>{location_label}:</b> {_esc(_format_address(order))}",
            f"<b>{_('Time:')}</b> {_esc(_format_timeslot(order))}",
            f"<b>{_('Payment:')}</b> {payment}",
            f"<b>{_('Total:')}</b> {_format_money(order.total)}",
        ]
    )
    if order.discount_total > 0:
        lines.append(f"<b>{_('Discount:')}</b> −{_format_money(order.discount_total)}")
    if order.comment:
        lines.append(f"<b>{_('Comment:')}</b> {_esc(order.comment)}")
    lines.extend(
        [
            "",
            f"<b>{_('Items:')}</b>",
            _format_items(order),
            "",
            f'<a href="{admin_url}">{_("Open in admin")}</a>',
        ]
    )
    return "\n".join(lines)


def send_order_notification(order: Order) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return
    from django.utils import translation

    prev = translation.get_language()
    translation.activate(order.locale)
    text = build_order_notification_text(order)
    translation.activate(prev)

    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req)
