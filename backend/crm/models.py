from django.db import models


class CrmOrder(models.Model):
    FULFILLMENT_DELIVERY = "delivery"
    FULFILLMENT_PICKUP = "pickup"
    FULFILLMENT_CHOICES = [
        (FULFILLMENT_DELIVERY, "Delivery"),
        (FULFILLMENT_PICKUP, "Pickup"),
    ]

    PAYMENT_UNKNOWN = "unknown"
    PAYMENT_CASH = "cash"
    PAYMENT_TERMINAL = "terminal"
    PAYMENT_TBC = "tbc"
    PAYMENT_BOG = "bog"
    PAYMENT_FLOWWOW = "flowwow"
    PAYMENT_CRYPTO = "crypto"
    PAYMENT_TYPE_CHOICES = [
        (PAYMENT_UNKNOWN, "Unknown"),
        (PAYMENT_CASH, "Cash"),
        (PAYMENT_TERMINAL, "Terminal"),
        (PAYMENT_TBC, "TBC Transfer"),
        (PAYMENT_BOG, "BOG Transfer"),
        (PAYMENT_FLOWWOW, "Flowwow"),
        (PAYMENT_CRYPTO, "Cryptocurrency"),
    ]

    date = models.DateField()
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    when_ready = models.BooleanField(default=False)
    contact = models.TextField()
    nickname = models.CharField(max_length=100, blank=True)
    delivery_address = models.TextField(blank=True)
    fulfillment_type = models.CharField(
        max_length=10,
        choices=FULFILLMENT_CHOICES,
        default=FULFILLMENT_DELIVERY,
    )
    is_delivered = models.BooleanField(default=False)
    weight = models.CharField(max_length=50)
    filling = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cake_price = models.DecimalField(max_digits=10, decimal_places=2)
    prepayment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default=PAYMENT_UNKNOWN,
    )
    deleted = models.BooleanField(default=False)
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    telegram_media_ids = models.JSONField(default=list)
    telegram_payload_hash = models.CharField(max_length=64, blank=True, default="")
    telegram_posted_date = models.DateField(null=True, blank=True)
    telegram_posted_time_start = models.TimeField(null=True, blank=True)
    telegram_posted_time_end = models.TimeField(null=True, blank=True)
    telegram_posted_when_ready = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "time_start"]

    def __str__(self) -> str:
        if self.when_ready:
            time_display = "when ready"
        elif self.time_start is None:
            time_display = "unknown"
        elif self.time_end:
            time_display = (
                f"{self.time_start.strftime('%H:%M')}-{self.time_end.strftime('%H:%M')}"
            )
        else:
            time_display = self.time_start.strftime("%H:%M")
        return f"{self.date} {time_display} - {self.contact[:30]}"


class ResolvedYandexAddress(models.Model):
    address = models.TextField(unique=True)
    yandex_url = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.address[:50]


class YandexAddressResolveFailure(models.Model):
    address = models.TextField(unique=True)
    failure_count = models.PositiveSmallIntegerField()


class CrmOrderImage(models.Model):
    order = models.ForeignKey(CrmOrder, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="crm_orders/")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"Image #{self.pk} for CrmOrder #{self.order_id}"


class WhatsAppNumberCheck(CrmOrder):
    class Meta:
        proxy = True
        verbose_name = "WhatsApp number check"
        verbose_name_plural = "WhatsApp number check"
