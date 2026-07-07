from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from orders.liberty import liberty_pay_enabled_for_request
from orders.models import (
    DeliveryAddress,
    Order,
    OrderItem,
    OrderItemOption,
    PickupLocation,
)


class PickupLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocation
        fields = ["id", "name", "address", "lat", "lng"]


class OrderItemOptionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItemOption
        fields = ["group_name", "option_name", "price_delta"]


class OrderItemReadSerializer(serializers.ModelSerializer):
    options = OrderItemOptionReadSerializer(many=True, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product_name", "unit_price", "quantity", "comment", "line_total", "options"]


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = ["street", "building", "apartment", "city", "postal_code", "notes", "lat", "lng"]


class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemReadSerializer(many=True, read_only=True)
    delivery_address = DeliveryAddressSerializer(read_only=True)
    pickup_location = PickupLocationSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "number",
            "lookup_token",
            "locale",
            "fulfillment_type",
            "status",
            "payment_method",
            "payment_status",
            "customer_name",
            "customer_phone",
            "customer_email",
            "customer_instagram",
            "customer_telegram",
            "comment",
            "pickup_location",
            "delivery_address",
            "timeslot_start",
            "timeslot_end",
            "subtotal",
            "discount_total",
            "delivery_fee",
            "total",
            "items",
            "created_at",
        ]


class AddressInputSerializer(serializers.Serializer):
    street = serializers.CharField()
    building = serializers.CharField(required=False, allow_blank=True, default="")
    apartment = serializers.CharField(required=False, allow_blank=True, default="")
    city = serializers.CharField()
    postal_code = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    lat = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)


class OrderPreviewInputSerializer(serializers.Serializer):
    fulfillment_type = serializers.ChoiceField(choices=Order.FULFILLMENT_CHOICES)
    address = AddressInputSerializer(required=False, allow_null=True)
    pickup_location_id = serializers.IntegerField(required=False, allow_null=True)
    promo_code = serializers.CharField(required=False, allow_blank=True, default="")


class OrderCreateInputSerializer(serializers.Serializer):
    fulfillment_type = serializers.ChoiceField(choices=Order.FULFILLMENT_CHOICES)
    address = AddressInputSerializer(required=False, allow_null=True)
    pickup_location_id = serializers.IntegerField(required=False, allow_null=True)
    schedule_mode = serializers.ChoiceField(choices=["slot"])
    schedule_date = serializers.DateField(required=False, allow_null=True)
    schedule_start_time = serializers.TimeField(required=False, allow_null=True)
    schedule_end_time = serializers.TimeField(required=False, allow_null=True)
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_METHOD_CHOICES)
    customer_name = serializers.CharField(max_length=200)
    customer_phone = serializers.CharField(max_length=50)
    customer_email = serializers.EmailField(required=False, allow_blank=True, default="")
    customer_instagram = serializers.CharField(required=False, allow_blank=True, default="", max_length=100)
    customer_telegram = serializers.CharField(required=False, allow_blank=True, default="", max_length=100)
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    promo_code = serializers.CharField(required=False, allow_blank=True, default="")
    locale = serializers.ChoiceField(choices=["en", "ka", "ru"])

    def validate(self, attrs):
        if attrs.get("schedule_date") is None:
            raise serializers.ValidationError(
                {"schedule_date": _("This field is required for a scheduled slot.")}
            )
        if attrs.get("schedule_start_time") is None:
            raise serializers.ValidationError(
                {"schedule_start_time": _("This field is required for a scheduled slot.")}
            )
        if attrs.get("schedule_end_time") is None:
            raise serializers.ValidationError(
                {"schedule_end_time": _("This field is required for a scheduled slot.")}
            )
        request = self.context.get("request")
        if (
            attrs.get("payment_method") == Order.PAYMENT_CARD
            and request is not None
            and not liberty_pay_enabled_for_request(request)
        ):
            raise serializers.ValidationError(
                {"payment_method": _("Card payment is not available.")}
            )
        return attrs


class PromoValidateInputSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)


class LibertyPaymentStartInputSerializer(serializers.Serializer):
    number = serializers.CharField(max_length=20)
    token = serializers.UUIDField()
