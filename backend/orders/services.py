import threading
from decimal import Decimal

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from rest_framework import serializers

from cart.models import Cart
from orders.schedule import resolve_schedule_selection
from orders.telegram import send_order_notification
from orders.models import (
    DeliveryAddress,
    Order,
    OrderItem,
    OrderItemOption,
    PickupLocation,
    PromoCode,
)


def compute_promo_discount(promo: PromoCode | None, subtotal: Decimal) -> Decimal:
    if promo is None:
        return Decimal("0")
    now = timezone.now()
    if not promo.is_active:
        raise serializers.ValidationError({"promo_code": _("Promo code is not active.")})
    if promo.valid_from and now < promo.valid_from:
        raise serializers.ValidationError({"promo_code": _("Promo code is not yet valid.")})
    if promo.valid_to and now > promo.valid_to:
        raise serializers.ValidationError({"promo_code": _("Promo code has expired.")})
    if promo.max_uses is not None and promo.uses_count >= promo.max_uses:
        raise serializers.ValidationError({"promo_code": _("Promo code usage limit reached.")})
    if subtotal < promo.min_order_amount:
        raise serializers.ValidationError(
            {"promo_code": _("Minimum order amount is %(amount)s.") % {"amount": promo.min_order_amount}}
        )

    if promo.discount_type == PromoCode.DISCOUNT_PERCENT:
        discount = (subtotal * promo.discount_value / Decimal("100")).quantize(Decimal("0.01"))
    else:
        discount = promo.discount_value
    if discount > subtotal:
        discount = subtotal
    return discount


def get_promo_by_code(code: str) -> PromoCode:
    promo = PromoCode.objects.filter(code__iexact=code).first()
    if promo is None:
        raise serializers.ValidationError({"promo_code": _("Promo code not found.")})
    return promo


def compute_totals(cart: Cart, promo: PromoCode | None) -> dict:
    subtotal = cart.subtotal
    discount = compute_promo_discount(promo, subtotal)
    total = subtotal - discount
    return {"subtotal": subtotal, "discount_total": discount, "total": total}


@transaction.atomic
def create_order_from_cart(cart: Cart, payload: dict) -> Order:
    if not cart.items.exists():
        raise serializers.ValidationError({"cart": _("Cart is empty.")})

    fulfillment_type = payload["fulfillment_type"]

    pickup_location: PickupLocation | None = None
    if fulfillment_type == Order.FULFILLMENT_PICKUP:
        pickup_id = payload.get("pickup_location_id")
        if pickup_id is None:
            raise serializers.ValidationError(
                {"pickup_location_id": _("Pickup location is required.")}
            )
        pickup_location = PickupLocation.objects.filter(pk=pickup_id, is_active=True).first()
        if pickup_location is None:
            raise serializers.ValidationError(
                {"pickup_location_id": _("Pickup location not found.")}
            )

    address_data: dict | None = None
    if fulfillment_type == Order.FULFILLMENT_DELIVERY:
        address_data = payload.get("address")
        if not address_data:
            raise serializers.ValidationError({"address": _("Delivery address is required.")})

    timeslot_start, timeslot_end = resolve_schedule_selection(
        cart,
        payload["schedule_mode"],
        payload.get("schedule_date"),
        payload.get("schedule_start_time"),
        payload.get("schedule_end_time"),
    )

    promo: PromoCode | None = None
    if payload.get("promo_code"):
        promo = get_promo_by_code(payload["promo_code"])

    totals = compute_totals(cart, promo)

    order = Order.objects.create(
        locale=payload["locale"],
        fulfillment_type=fulfillment_type,
        payment_method=payload["payment_method"],
        customer_name=payload["customer_name"],
        customer_phone=payload["customer_phone"],
        customer_email=payload.get("customer_email", ""),
        customer_instagram=payload.get("customer_instagram", ""),
        customer_telegram=payload.get("customer_telegram", ""),
        comment=payload.get("comment", ""),
        promo_code=promo,
        pickup_location=pickup_location,
        timeslot_start=timeslot_start,
        timeslot_end=timeslot_end,
        subtotal=totals["subtotal"],
        discount_total=totals["discount_total"],
        total=totals["total"],
    )

    if address_data is not None:
        DeliveryAddress.objects.create(
            order=order,
            street=address_data["street"],
            building=address_data.get("building", ""),
            apartment=address_data.get("apartment", ""),
            city=address_data["city"],
            postal_code=address_data.get("postal_code", ""),
            notes=address_data.get("notes", ""),
            lat=address_data.get("lat"),
            lng=address_data.get("lng"),
        )

    items = list(
        cart.items.select_related("product").prefetch_related("options__option__group")
    )
    for cart_item in items:
        order_item = OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            product_name=cart_item.product.name,
            unit_price=cart_item.unit_price,
            quantity=cart_item.quantity,
            comment=cart_item.comment,
            line_total=cart_item.line_total,
        )
        for co in cart_item.options.all():
            OrderItemOption.objects.create(
                order_item=order_item,
                group_name=co.option.group.name,
                option_name=co.option.name,
                price_delta=co.option.price_delta,
            )

    if promo is not None:
        PromoCode.objects.filter(pk=promo.pk).update(uses_count=promo.uses_count + 1)

    cart.is_ordered = True
    cart.save()

    order_id = order.pk
    transaction.on_commit(
        lambda: threading.Thread(
            target=_send_order_telegram_notification,
            args=(order_id,),
            daemon=True,
        ).start()
    )

    return order


def _send_order_telegram_notification(order_id: int) -> None:
    order = (
        Order.objects.select_related("pickup_location", "delivery_address")
        .prefetch_related("items__options")
        .get(pk=order_id)
    )
    send_order_notification(order)
