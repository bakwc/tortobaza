import secrets
import uuid

from django.db import models

from catalog.models import Product


class PromoCode(models.Model):
    DISCOUNT_PERCENT = "percent"
    DISCOUNT_FIXED = "fixed"
    DISCOUNT_CHOICES = [
        (DISCOUNT_PERCENT, "Percent"),
        (DISCOUNT_FIXED, "Fixed"),
    ]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_CHOICES, default=DISCOUNT_PERCENT)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    uses_count = models.PositiveIntegerField(default=0)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class PickupLocation(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

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
        (FULFILLMENT_DELIVERY, "Delivery"),
        (FULFILLMENT_PICKUP, "Pickup"),
    ]

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_PREPARING = "preparing"
    STATUS_READY = "ready"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_PREPARING, "Preparing"),
        (STATUS_READY, "Ready"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    PAYMENT_CARD = "card"
    PAYMENT_CASH = "cash"
    PAYMENT_BANK_TRANSFER = "bank_transfer"
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_CARD, "Card"),
        (PAYMENT_CASH, "Cash"),
        (PAYMENT_BANK_TRANSFER, "Bank transfer"),
    ]

    PAYMENT_UNPAID = "unpaid"
    PAYMENT_PAID = "paid"
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_UNPAID, "Unpaid"),
        (PAYMENT_PAID, "Paid"),
    ]

    number = models.CharField(max_length=20, unique=True, default=_generate_order_number, editable=False)
    lookup_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    locale = models.CharField(max_length=5, default="en")

    fulfillment_type = models.CharField(max_length=10, choices=FULFILLMENT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_UNPAID)

    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=50)
    customer_email = models.EmailField(blank=True)
    customer_instagram = models.CharField(max_length=100, blank=True)
    customer_telegram = models.CharField(max_length=100, blank=True)
    comment = models.TextField(blank=True)

    promo_code = models.ForeignKey(PromoCode, related_name="orders", on_delete=models.SET_NULL, null=True, blank=True)
    pickup_location = models.ForeignKey(
        PickupLocation, related_name="orders", on_delete=models.SET_NULL, null=True, blank=True
    )

    timeslot_start = models.DateTimeField(null=True, blank=True)
    timeslot_end = models.DateTimeField(null=True, blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order {self.number}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="+", on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    comment = models.TextField(blank=True)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.product_name} x{self.quantity}"


class OrderItemOption(models.Model):
    order_item = models.ForeignKey(OrderItem, related_name="options", on_delete=models.CASCADE)
    group_name = models.CharField(max_length=120)
    option_name = models.CharField(max_length=120)
    price_delta = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.group_name}: {self.option_name}"


class LibertyPayment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELED, "Canceled"),
        (STATUS_ERROR, "Error"),
    ]

    order = models.ForeignKey(Order, related_name="liberty_payments", on_delete=models.CASCADE)
    ordercode = models.CharField(max_length=50, unique=True)
    transaction_code = models.CharField(max_length=20, blank=True)
    amount_tetri = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="GEL")
    pay_method = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    testmode = models.BooleanField(default=False)
    raw_callback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.ordercode} ({self.status})"


class DeliveryAddress(models.Model):
    order = models.OneToOneField(Order, related_name="delivery_address", on_delete=models.CASCADE)
    street = models.CharField(max_length=200)
    building = models.CharField(max_length=50, blank=True)
    apartment = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.street} {self.building}, {self.city}"
