from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from orders.models import (
    DeliveryAddress,
    Order,
    OrderItem,
    OrderItemOption,
    PickupLocation,
    PromoCode,
)


class OrderItemOptionInline(admin.TabularInline):
    model = OrderItemOption
    extra = 0
    readonly_fields = ["group_name", "option_name", "price_delta"]
    can_delete = False


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "product_name", "unit_price", "quantity", "comment", "line_total"]
    can_delete = False
    show_change_link = True


class DeliveryAddressInline(admin.StackedInline):
    model = DeliveryAddress
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "number",
        "fulfillment_type",
        "status",
        "payment_method",
        "payment_status",
        "customer_name",
        "total",
        "created_at",
    ]
    list_filter = ["status", "fulfillment_type", "payment_method", "payment_status"]
    search_fields = [
        "number",
        "customer_name",
        "customer_phone",
        "customer_email",
        "customer_instagram",
        "customer_telegram",
    ]
    readonly_fields = [
        "number",
        "lookup_token",
        "subtotal",
        "discount_total",
        "delivery_fee",
        "total",
        "created_at",
    ]
    inlines = [OrderItemInline, DeliveryAddressInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "product_name", "unit_price", "quantity", "line_total"]
    inlines = [OrderItemOptionInline]


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "discount_type",
        "discount_value",
        "valid_from",
        "valid_to",
        "max_uses",
        "uses_count",
        "is_active",
    ]
    list_filter = ["discount_type", "is_active"]
    search_fields = ["code"]


@admin.register(PickupLocation)
class PickupLocationAdmin(TranslationAdmin):
    list_display = ["name", "address", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "address"]
