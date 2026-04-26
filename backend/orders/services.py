from datetime import datetime, time
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from cart.models import Cart, CartItem
from orders.models import (
    DeliveryAddress,
    DeliveryTimeslot,
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
        raise serializers.ValidationError({"promo_code": "Promo code is not active."})
    if promo.valid_from and now < promo.valid_from:
        raise serializers.ValidationError({"promo_code": "Promo code is not yet valid."})
    if promo.valid_to and now > promo.valid_to:
        raise serializers.ValidationError({"promo_code": "Promo code has expired."})
    if promo.max_uses is not None and promo.uses_count >= promo.max_uses:
        raise serializers.ValidationError({"promo_code": "Promo code usage limit reached."})
    if subtotal < promo.min_order_amount:
        raise serializers.ValidationError(
            {"promo_code": f"Minimum order amount is {promo.min_order_amount}."}
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
        raise serializers.ValidationError({"promo_code": "Promo code not found."})
    return promo


def compute_totals(cart: Cart, promo: PromoCode | None) -> dict:
    subtotal = cart.subtotal
    discount = compute_promo_discount(promo, subtotal)
    total = subtotal - discount
    return {"subtotal": subtotal, "discount_total": discount, "total": total}


def _check_timeslot_capacity(timeslot: DeliveryTimeslot) -> None:
    if not timeslot.is_active:
        raise serializers.ValidationError({"timeslot_id": "Timeslot is not available."})
    booked = Order.objects.filter(timeslot=timeslot).exclude(status=Order.STATUS_CANCELLED).count()
    if booked >= timeslot.capacity:
        raise serializers.ValidationError({"timeslot_id": "Timeslot has no remaining capacity."})


def _resolve_timeslot(
    timeslot_id: int | None, fulfillment_type: str
) -> DeliveryTimeslot | None:
    if timeslot_id is None:
        return None
    timeslot = DeliveryTimeslot.objects.filter(pk=timeslot_id).first()
    if timeslot is None:
        raise serializers.ValidationError({"timeslot_id": "Timeslot not found."})
    if timeslot.fulfillment_type not in (fulfillment_type, DeliveryTimeslot.FULFILLMENT_BOTH):
        raise serializers.ValidationError(
            {"timeslot_id": "Timeslot does not match fulfillment type."}
        )
    _check_timeslot_capacity(timeslot)
    return timeslot


def _timeslot_datetimes(slot: DeliveryTimeslot) -> tuple[datetime, datetime]:
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(slot.date, slot.start_time), tz)
    end = timezone.make_aware(datetime.combine(slot.date, slot.end_time), tz)
    return start, end


@transaction.atomic
def create_order_from_cart(cart: Cart, payload: dict) -> Order:
    if not cart.items.exists():
        raise serializers.ValidationError({"cart": "Cart is empty."})

    fulfillment_type = payload["fulfillment_type"]

    pickup_location: PickupLocation | None = None
    if fulfillment_type == Order.FULFILLMENT_PICKUP:
        pickup_id = payload.get("pickup_location_id")
        if pickup_id is None:
            raise serializers.ValidationError(
                {"pickup_location_id": "Pickup location is required."}
            )
        pickup_location = PickupLocation.objects.filter(pk=pickup_id, is_active=True).first()
        if pickup_location is None:
            raise serializers.ValidationError(
                {"pickup_location_id": "Pickup location not found."}
            )

    address_data: dict | None = None
    if fulfillment_type == Order.FULFILLMENT_DELIVERY:
        address_data = payload.get("address")
        if not address_data:
            raise serializers.ValidationError({"address": "Delivery address is required."})

    timeslot = _resolve_timeslot(payload.get("timeslot_id"), fulfillment_type)

    promo: PromoCode | None = None
    if payload.get("promo_code"):
        promo = get_promo_by_code(payload["promo_code"])

    totals = compute_totals(cart, promo)

    timeslot_start = timeslot_end = None
    if timeslot is not None:
        timeslot_start, timeslot_end = _timeslot_datetimes(timeslot)

    order = Order.objects.create(
        fulfillment_type=fulfillment_type,
        payment_method=payload["payment_method"],
        customer_name=payload["customer_name"],
        customer_phone=payload["customer_phone"],
        customer_email=payload.get("customer_email", ""),
        comment=payload.get("comment", ""),
        promo_code=promo,
        pickup_location=pickup_location,
        timeslot=timeslot,
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

    return order
