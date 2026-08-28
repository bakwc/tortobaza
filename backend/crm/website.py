from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from django.core.files.base import ContentFile
from django.utils import timezone

from crm.models import CrmOrder, CrmOrderImage
from crm.telegram import schedule_crm_order_telegram_sync
from orders.models import Order, OrderItem

_TB = ZoneInfo("Asia/Tbilisi")

_WEIGHT_GROUPS = frozenset({"weight", "size", "вес", "размер"})
_FILLING_GROUPS = frozenset({"filling", "начинка"})

_PAYMENT_MAP = {
    Order.PAYMENT_CARD: CrmOrder.PAYMENT_ONLINE,
    Order.PAYMENT_CASH: CrmOrder.PAYMENT_CASH,
    Order.PAYMENT_BANK_TRANSFER: CrmOrder.PAYMENT_UNKNOWN,
}


def create_crm_order_from_website_order(order: Order) -> CrmOrder | None:
    if order.environment == Order.ENV_DEV:
        return None
    start = timezone.localtime(order.timeslot_start, _TB)
    end = timezone.localtime(order.timeslot_end, _TB)
    weight_parts = _option_names(order, _WEIGHT_GROUPS)
    filling_parts = _option_names(order, _FILLING_GROUPS)
    product_names = [_item_label(item) for item in order.items.all()]
    nickname = order.customer_instagram or order.customer_telegram
    crm_order = CrmOrder.objects.create(
        date=start.date(),
        time_start=start.time().replace(second=0, microsecond=0),
        time_end=end.time().replace(second=0, microsecond=0),
        when_ready=False,
        contact=f"{order.customer_name} {order.customer_phone}".strip(),
        nickname=nickname,
        delivery_address=_format_address(order),
        fulfillment_type=order.fulfillment_type,
        weight=", ".join(weight_parts) if weight_parts else "—",
        filling=", ".join(filling_parts) if filling_parts else ", ".join(product_names),
        description=_build_description(order),
        cake_price=order.total,
        prepayment=Decimal("0"),
        is_paid=False,
        payment_type=_PAYMENT_MAP[order.payment_method],
        website_order=order,
    )
    _copy_product_images(order, crm_order)
    schedule_crm_order_telegram_sync(crm_order.pk)
    return crm_order


def mark_crm_order_paid_for_website_order(order: Order) -> None:
    if order.environment == Order.ENV_DEV:
        return
    crm_order = CrmOrder.objects.get(website_order=order)
    crm_order.is_paid = True
    crm_order.prepayment = crm_order.cake_price
    crm_order.save(update_fields=["is_paid", "prepayment", "updated_at"])
    schedule_crm_order_telegram_sync(crm_order.pk)


def _option_names(order: Order, groups: frozenset[str]) -> list[str]:
    names: list[str] = []
    for item in order.items.all():
        for opt in item.options.all():
            if opt.group_name.casefold() in groups:
                names.append(opt.option_name)
    return names


def _item_label(item: OrderItem) -> str:
    if item.quantity == 1:
        return item.product_name
    return f"{item.product_name} × {item.quantity}"


def _format_address(order: Order) -> str:
    if order.fulfillment_type == Order.FULFILLMENT_PICKUP:
        loc = order.pickup_location
        return f"{loc.name}, {loc.address}"
    addr = order.delivery_address
    parts = [addr.street]
    if addr.building:
        parts.append(addr.building)
    if addr.apartment:
        parts.append(addr.apartment)
    line = ", ".join(parts)
    if addr.city:
        line = f"{line}, {addr.city}"
    if addr.notes:
        line = f"{line} ({addr.notes})"
    return line


def _build_description(order: Order) -> str:
    lines = [f"Сайт заказ #{order.number}"]
    for item in order.items.all():
        line = f"{item.product_name} × {item.quantity} — {item.line_total}"
        options = list(item.options.all())
        if options:
            opt_parts = [f"{o.group_name}: {o.option_name}" for o in options]
            line += f"\n  {', '.join(opt_parts)}"
        if item.comment:
            line += f"\n  {item.comment}"
        lines.append(line)
    if order.customer_email:
        lines.append(f"Email: {order.customer_email}")
    if order.promo_code_id:
        lines.append(f"Промокод: {order.promo_code.code}")
    if order.delivery_fee > 0:
        lines.append(f"Доставка: {order.delivery_fee}")
    if order.comment:
        lines.append(order.comment)
    return "\n".join(lines)


def _copy_product_images(order: Order, crm_order: CrmOrder) -> None:
    position = 0
    for item in order.items.all():
        product = item.product
        if product is None:
            continue
        for pimg in product.images.all():
            pimg.image.open("rb")
            content = pimg.image.read()
            pimg.image.close()
            name = Path(pimg.image.name).name
            CrmOrderImage.objects.create(
                order=crm_order,
                image=ContentFile(content, name=name),
                position=position,
            )
            position += 1
