import secrets
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from catalog.models import Product


class PromoCode(models.Model):
    DISCOUNT_PERCENT = "percent"
    DISCOUNT_FIXED = "fixed"
    DISCOUNT_CHOICES = [
        (DISCOUNT_PERCENT, _("Percent")),
        (DISCOUNT_FIXED, _("Fixed")),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name=_("Code"))
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_CHOICES,
        default=DISCOUNT_PERCENT,
        verbose_name=_("Discount type"),
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Discount value"))
    valid_from = models.DateTimeField(null=True, blank=True, verbose_name=_("Valid from"))
    valid_to = models.DateTimeField(null=True, blank=True, verbose_name=_("Valid to"))
    max_uses = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Max uses"))
    uses_count = models.PositiveIntegerField(default=0, verbose_name=_("Uses count"))
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Minimum order amount"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    class Meta:
        ordering = ["code"]
        verbose_name = _("Promo code")
        verbose_name_plural = _("Promo codes")

    def __str__(self) -> str:
        return self.code


class PickupLocation(models.Model):
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    address = models.CharField(max_length=300, verbose_name=_("Address"))
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_("Latitude"))
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_("Longitude"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    class Meta:
        ordering = ["name"]
        verbose_name = _("Pickup location")
        verbose_name_plural = _("Pickup locations")

    def __str__(self) -> str:
        return self.name


ORDER_NUMBER_START = 73000
ORDER_NUMBER_STEP_MIN = 4
ORDER_NUMBER_STEP_MAX = 18


def _generate_order_number() -> str:
    numeric_numbers = [
        int(number)
        for number in Order.objects.values_list("number", flat=True)
        if number.isdigit()
    ]
    if not numeric_numbers:
        return str(ORDER_NUMBER_START)
    step = secrets.randbelow(ORDER_NUMBER_STEP_MAX - ORDER_NUMBER_STEP_MIN + 1) + ORDER_NUMBER_STEP_MIN
    return str(max(numeric_numbers) + step)


class Order(models.Model):
    FULFILLMENT_DELIVERY = "delivery"
    FULFILLMENT_PICKUP = "pickup"
    FULFILLMENT_CHOICES = [
        (FULFILLMENT_DELIVERY, _("Delivery")),
        (FULFILLMENT_PICKUP, _("Pickup")),
    ]

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_PREPARING = "preparing"
    STATUS_READY = "ready"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_CONFIRMED, _("Confirmed")),
        (STATUS_PREPARING, _("Preparing")),
        (STATUS_READY, _("Ready")),
        (STATUS_DELIVERED, _("Delivered")),
        (STATUS_CANCELLED, _("Cancelled")),
    ]

    PAYMENT_CARD = "card"
    PAYMENT_CASH = "cash"
    PAYMENT_BANK_TRANSFER = "bank_transfer"
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_CARD, _("Card")),
        (PAYMENT_CASH, _("Cash")),
        (PAYMENT_BANK_TRANSFER, _("Bank transfer")),
    ]

    PAYMENT_UNPAID = "unpaid"
    PAYMENT_PAID = "paid"
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_UNPAID, _("Unpaid")),
        (PAYMENT_PAID, _("Paid")),
    ]

    ENV_PROD = "prod"
    ENV_DEV = "dev"
    ENVIRONMENT_CHOICES = [
        (ENV_PROD, _("Production")),
        (ENV_DEV, _("Development")),
    ]

    number = models.CharField(
        max_length=20,
        unique=True,
        default=_generate_order_number,
        editable=False,
        verbose_name=_("Number"),
    )
    lookup_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name=_("Lookup token"))

    locale = models.CharField(max_length=5, default="en", verbose_name=_("Locale"))
    environment = models.CharField(
        max_length=10,
        choices=ENVIRONMENT_CHOICES,
        default=ENV_PROD,
        verbose_name=_("Environment"),
    )

    fulfillment_type = models.CharField(
        max_length=10,
        choices=FULFILLMENT_CHOICES,
        verbose_name=_("Fulfillment type"),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name=_("Status"),
    )
    payment_method = models.CharField(
        max_length=15,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name=_("Payment method"),
    )
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_UNPAID,
        verbose_name=_("Payment status"),
    )

    customer_name = models.CharField(max_length=200, verbose_name=_("Customer name"))
    customer_phone = models.CharField(max_length=50, verbose_name=_("Customer phone"))
    customer_email = models.EmailField(verbose_name=_("Customer email"))
    customer_instagram = models.CharField(max_length=100, blank=True, verbose_name=_("Customer Instagram"))
    customer_telegram = models.CharField(max_length=100, blank=True, verbose_name=_("Customer Telegram"))
    comment = models.TextField(blank=True, verbose_name=_("Comment"))

    promo_code = models.ForeignKey(
        PromoCode,
        related_name="orders",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Promo code"),
    )
    pickup_location = models.ForeignKey(
        PickupLocation,
        related_name="orders",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Pickup location"),
    )

    timeslot_start = models.DateTimeField(null=True, blank=True, verbose_name=_("Timeslot start"))
    timeslot_end = models.DateTimeField(null=True, blank=True, verbose_name=_("Timeslot end"))

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Subtotal"))
    discount_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Discount total"),
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        db_default=0,
        verbose_name=_("Delivery fee"),
    )
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Total"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self) -> str:
        return f"Order {self.number}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE, verbose_name=_("Order"))
    product = models.ForeignKey(
        Product,
        related_name="+",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Product"),
    )
    product_name = models.CharField(max_length=200, verbose_name=_("Product name"))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Unit price"))
    quantity = models.PositiveIntegerField(verbose_name=_("Quantity"))
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    line_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Line total"))

    class Meta:
        ordering = ["id"]
        verbose_name = _("Order item")
        verbose_name_plural = _("Order items")

    def __str__(self) -> str:
        return f"{self.product_name} x{self.quantity}"


class OrderItemOption(models.Model):
    order_item = models.ForeignKey(
        OrderItem,
        related_name="options",
        on_delete=models.CASCADE,
        verbose_name=_("Order item"),
    )
    group_name = models.CharField(max_length=120, verbose_name=_("Group name"))
    option_name = models.CharField(max_length=120, verbose_name=_("Option name"))
    price_delta = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Price delta"))

    class Meta:
        ordering = ["id"]
        verbose_name = _("Order item option")
        verbose_name_plural = _("Order item options")

    def __str__(self) -> str:
        return f"{self.group_name}: {self.option_name}"


class LibertyPayment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_COMPLETED, _("Completed")),
        (STATUS_CANCELED, _("Canceled")),
        (STATUS_ERROR, _("Error")),
    ]

    order = models.ForeignKey(Order, related_name="liberty_payments", on_delete=models.CASCADE, verbose_name=_("Order"))
    ordercode = models.CharField(max_length=50, unique=True, verbose_name=_("Order code"))
    transaction_code = models.CharField(max_length=20, blank=True, verbose_name=_("Transaction code"))
    amount_tetri = models.PositiveIntegerField(verbose_name=_("Amount in tetri"))
    currency = models.CharField(max_length=3, default="GEL", verbose_name=_("Currency"))
    pay_method = models.CharField(max_length=20, blank=True, verbose_name=_("Pay method"))
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name=_("Status"),
    )
    testmode = models.BooleanField(default=False, verbose_name=_("Test mode"))
    raw_callback = models.TextField(blank=True, verbose_name=_("Raw callback"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Liberty payment")
        verbose_name_plural = _("Liberty payments")

    def __str__(self) -> str:
        return f"{self.ordercode} ({self.status})"


class DeliveryAddress(models.Model):
    order = models.OneToOneField(Order, related_name="delivery_address", on_delete=models.CASCADE, verbose_name=_("Order"))
    street = models.CharField(max_length=200, verbose_name=_("Street"))
    building = models.CharField(max_length=50, blank=True, verbose_name=_("Building"))
    apartment = models.CharField(max_length=50, blank=True, verbose_name=_("Apartment"))
    city = models.CharField(max_length=120, verbose_name=_("City"))
    postal_code = models.CharField(max_length=20, blank=True, verbose_name=_("Postal code"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_("Latitude"))
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_("Longitude"))

    class Meta:
        verbose_name = _("Delivery address")
        verbose_name_plural = _("Delivery addresses")

    def __str__(self) -> str:
        return f"{self.street} {self.building}, {self.city}"
