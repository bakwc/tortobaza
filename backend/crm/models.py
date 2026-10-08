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
    delivery_distance_meters = models.PositiveIntegerField(null=True, blank=True)
    delivery_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    delivery_route_computed_at = models.DateTimeField(null=True, blank=True)
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
                update_fields = [*update_fields, "phones"]
                kwargs["update_fields"] = update_fields
        address_changed = False
        if self.pk is not None and (update_fields is None or "delivery_address" in update_fields):
            previous_address = (
                CrmOrder.objects.filter(pk=self.pk)
                .values_list("delivery_address", flat=True)
                .first()
            )
            if previous_address != self.delivery_address:
                address_changed = True
                self.delivery_distance_meters = None
                self.delivery_duration_seconds = None
                self.delivery_route_computed_at = None
                if update_fields is not None:
                    for name in (
                        "delivery_distance_meters",
                        "delivery_duration_seconds",
                        "delivery_route_computed_at",
                    ):
                        if name not in update_fields:
                            update_fields = [*update_fields, name]
                    kwargs["update_fields"] = update_fields
        super().save(*args, **kwargs)
        if address_changed:
            DeliveryRouteResolveFailure.objects.filter(order_id=self.pk).delete()


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


class DeliveryRouteResolveFailure(models.Model):
    order = models.OneToOneField(CrmOrder, on_delete=models.CASCADE)
    failure_count = models.PositiveSmallIntegerField()


class ResolvedTelegramPhone(models.Model):
    number = models.CharField(max_length=15, unique=True)
    resolved = models.BooleanField()
    user_id = models.BigIntegerField(null=True, blank=True)
    username = models.CharField(max_length=32, blank=True, default="")
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Resolved Telegram phone"
        verbose_name_plural = "Resolved Telegram phones"

    def __str__(self) -> str:
        return self.number


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


class FinancialAccount(models.Model):
    KIND_BANK = "bank"
    KIND_CASH = "cash"
    KIND_CRYPTO = "crypto"
    KIND_VIRTUAL = "virtual"
    KIND_CHOICES = [
        (KIND_BANK, "Bank"),
        (KIND_CASH, "Cash"),
        (KIND_CRYPTO, "Crypto"),
        (KIND_VIRTUAL, "Virtual"),
    ]

    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    bank_name = models.CharField(max_length=100, blank=True)
    iban = models.CharField(max_length=34, blank=True)
    currency = models.CharField(max_length=3, default="GEL")

    def __str__(self) -> str:
        return self.name


class FinancialTransaction(models.Model):
    KIND_INCOME = "income"
    KIND_EXPENSE = "expense"
    KIND_TRANSFER = "transfer"
    KIND_WITHDRAWAL = "withdrawal"
    KIND_INVESTMENT = "investment"
    KIND_CORRECTION = "correction"
    KIND_OTHER = "other"
    KIND_CHOICES = [
        (KIND_INCOME, "Income"),
        (KIND_EXPENSE, "Expense"),
        (KIND_TRANSFER, "Transfer"),
        (KIND_WITHDRAWAL, "Withdrawal"),
        (KIND_INVESTMENT, "Investment"),
        (KIND_CORRECTION, "Correction"),
        (KIND_OTHER, "Other"),
    ]

    EXPENSE_SALARY = "salary"
    EXPENSE_RENT = "rent"
    EXPENSE_PRODUCTS = "products"
    EXPENSE_CONSUMABLES = "consumables"
    EXPENSE_EQUIPMENT = "equipment"
    EXPENSE_TYPE_CHOICES = [
        (EXPENSE_SALARY, "Salary"),
        (EXPENSE_RENT, "Rent"),
        (EXPENSE_PRODUCTS, "Products"),
        (EXPENSE_CONSUMABLES, "Consumables"),
        (EXPENSE_EQUIPMENT, "Equipment"),
    ]

    INCOME_ONLINE = "online"
    INCOME_TERMINAL = "terminal"
    INCOME_CASH = "cash"
    INCOME_TRANSFER = "transfer"
    INCOME_TYPE_CHOICES = [
        (INCOME_ONLINE, "Online"),
        (INCOME_TERMINAL, "Terminal"),
        (INCOME_CASH, "Cash"),
        (INCOME_TRANSFER, "Transfer"),
    ]

    account = models.ForeignKey(
        FinancialAccount,
        related_name="transactions",
        on_delete=models.PROTECT,
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    expense_type = models.CharField(
        max_length=20,
        choices=EXPENSE_TYPE_CHOICES,
        blank=True,
    )
    income_type = models.CharField(
        max_length=20,
        choices=INCOME_TYPE_CHOICES,
        blank=True,
    )
    transfer_id = models.UUIDField(null=True, blank=True)
    counterparty_name = models.CharField(max_length=255, blank=True)
    counterparty_iban = models.CharField(max_length=34, blank=True)
    description = models.TextField(blank=True)
    external_id = models.CharField(max_length=512, blank=True)
    crm_orders = models.ManyToManyField(
        CrmOrder,
        related_name="financial_transactions",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["date"], name="crm_fin_tx_date"),
            models.Index(fields=["transfer_id"], name="crm_fin_tx_transfer"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "external_id"],
                condition=~models.Q(external_id=""),
                name="uniq_fin_tx_account_external_id",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.amount} {self.account}"


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


class TelegramNumberCheck(CrmOrder):
    class Meta:
        proxy = True
        verbose_name = "Telegram number check"
        verbose_name_plural = "Telegram number check"
