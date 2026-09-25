import secrets
from datetime import time
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone

from crm.phone import phones_from_fields


def generate_crm_client_token() -> str:
    return secrets.token_hex(32)


class CrmSettings(models.Model):
    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        verbose_name = "CRM settings"
        verbose_name_plural = "CRM settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self) -> str:
        return "CRM settings"


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
    PAYMENT_ONLINE = "online"
    PAYMENT_TYPE_CHOICES = [
        (PAYMENT_UNKNOWN, "Unknown"),
        (PAYMENT_CASH, "Cash"),
        (PAYMENT_TERMINAL, "Terminal"),
        (PAYMENT_TBC, "TBC Transfer"),
        (PAYMENT_BOG, "BOG Transfer"),
        (PAYMENT_FLOWWOW, "Flowwow"),
        (PAYMENT_CRYPTO, "Cryptocurrency"),
        (PAYMENT_ONLINE, "Online on website"),
    ]

    date = models.DateField()
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    when_ready = models.BooleanField(default=False)
    contact = models.TextField()
    nickname = models.CharField(max_length=100, blank=True)
    phones = models.JSONField(default=list)
    delivery_address = models.TextField(blank=True)
    fulfillment_type = models.CharField(
        max_length=10,
        choices=FULFILLMENT_CHOICES,
        default=FULFILLMENT_DELIVERY,
    )
    STATUS_UNCONFIRMED = "unconfirmed"
    STATUS_NEW = "new"
    STATUS_IN_WORK = "in_work"
    STATUS_READY = "ready"
    STATUS_CLIENT_APPROVED = "client_approved"
    STATUS_IN_DELIVERY = "in_delivery"
    STATUS_DELIVERED = "delivered"
    STATUS_CHOICES = [
        (STATUS_UNCONFIRMED, "Unconfirmed"),
        (STATUS_NEW, "New"),
        (STATUS_IN_WORK, "In work"),
        (STATUS_READY, "Ready"),
        (STATUS_CLIENT_APPROVED, "Client approved"),
        (STATUS_IN_DELIVERY, "In delivery"),
        (STATUS_DELIVERED, "Delivered"),
    ]
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )
    taken_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_orders_taken",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_orders_created",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    delivered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_orders_delivered",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    weight = models.CharField(max_length=50)
    filling = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    internal_description = models.TextField(blank=True)
    cake_price = models.DecimalField(max_digits=10, decimal_places=2)
    prepayment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default=PAYMENT_UNKNOWN,
    )
    website_order = models.OneToOneField(
        "orders.Order",
        related_name="crm_order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    flowwow_order_id = models.IntegerField(unique=True, null=True, blank=True)
    flowwow_synced_description = models.TextField(blank=True, default="")
    flowwow_synced_internal_description = models.TextField(blank=True, default="")
    deleted = models.BooleanField(default=False)
    client_token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False,
        default=generate_crm_client_token,
    )
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    telegram_media_ids = models.JSONField(default=list)
    telegram_payload_hash = models.CharField(max_length=64, blank=True, default="")
    telegram_posted_date = models.DateField(null=True, blank=True)
    telegram_posted_time_start = models.TimeField(null=True, blank=True)
    telegram_posted_time_end = models.TimeField(null=True, blank=True)
    telegram_posted_when_ready = models.BooleanField(default=False)
    telegram_posted_delivery_address = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "date",
            Case(
                When(time_start=time(0, 0), then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            "time_start",
        ]

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

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields is None or "contact" in update_fields or "nickname" in update_fields:
            self.phones = phones_from_fields(self.contact, self.nickname)
            if update_fields is not None and "phones" not in update_fields:
                kwargs["update_fields"] = [*update_fields, "phones"]
        super().save(*args, **kwargs)


class CrmOrderEvent(models.Model):
    ACTION_CREATED = "created"
    ACTION_UPDATED = "updated"
    ACTION_DELETED = "deleted"
    ACTION_CHOICES = [
        (ACTION_CREATED, "Created"),
        (ACTION_UPDATED, "Updated"),
        (ACTION_DELETED, "Deleted"),
    ]

    SOURCE_CRM = "crm"
    SOURCE_ADMIN = "admin"
    SOURCE_WEBSITE = "website"
    SOURCE_FLOWWOW = "flowwow"
    SOURCE_CHOICES = [
        (SOURCE_CRM, "CRM"),
        (SOURCE_ADMIN, "Admin"),
        (SOURCE_WEBSITE, "Website"),
        (SOURCE_FLOWWOW, "Flowwow"),
    ]

    order = models.ForeignKey(CrmOrder, related_name="events", on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_order_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    changes = models.JSONField()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["order", "created_at"], name="crm_order_event_order_at"),
        ]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.source} order #{self.order_id}"


class ResolvedYandexAddress(models.Model):
    address = models.TextField(unique=True)
    yandex_url = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.address[:50]


class YandexAddressResolveFailure(models.Model):
    address = models.TextField(unique=True)
    failure_count = models.PositiveSmallIntegerField()


class ResolvedGoogleAddress(models.Model):
    address = models.TextField(unique=True)
    google_url = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.address[:50]


class GoogleAddressResolveFailure(models.Model):
    address = models.TextField(unique=True)
    failure_count = models.PositiveSmallIntegerField()


class CrmOrderImage(models.Model):
    order = models.ForeignKey(CrmOrder, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="crm_orders/")
    position = models.PositiveIntegerField(default=0)
    source_url = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "source_url"],
                name="uniq_crmorderimage_order_source_url",
            ),
        ]

    def __str__(self) -> str:
        return f"Image #{self.pk} for CrmOrder #{self.order_id}"


class FlowwowWebhookEvent(models.Model):
    uuid = models.CharField(max_length=36, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class WhatsAppNumberCheck(CrmOrder):
    class Meta:
        proxy = True
        verbose_name = "WhatsApp number check"
        verbose_name_plural = "WhatsApp number check"


class WhatsAppGetNewQr(CrmOrder):
    class Meta:
        proxy = True
        verbose_name = "WhatsApp get new QR"
        verbose_name_plural = "WhatsApp get new QR"
