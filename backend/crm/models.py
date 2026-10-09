import secrets
from datetime import time
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from crm.phone import phones_from_fields


def generate_crm_client_token() -> str:
    return secrets.token_hex(32)


class CrmSettings(models.Model):
    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Monthly rent"),
    )

    class Meta:
        verbose_name = _("CRM settings")
        verbose_name_plural = _("CRM settings")

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
        (FULFILLMENT_DELIVERY, _("Delivery")),
        (FULFILLMENT_PICKUP, _("Pickup")),
    ]

    PAYMENT_UNKNOWN = "unknown"
    PAYMENT_CASH = "cash"
    PAYMENT_TERMINAL = "terminal"
    PAYMENT_TBC = "tbc"
    PAYMENT_BOG = "bog"
    PAYMENT_TBANK = "tbank"
    PAYMENT_FLOWWOW = "flowwow"
    PAYMENT_CRYPTO = "crypto"
    PAYMENT_ONLINE = "online"
    PAYMENT_TYPE_CHOICES = [
        (PAYMENT_UNKNOWN, _("Unknown")),
        (PAYMENT_CASH, _("Cash")),
        (PAYMENT_TERMINAL, _("Terminal")),
        (PAYMENT_TBC, _("TBC Transfer")),
        (PAYMENT_BOG, _("BOG Transfer")),
        (PAYMENT_TBANK, _("T-Bank Transfer")),
        (PAYMENT_FLOWWOW, _("Flowwow")),
        (PAYMENT_CRYPTO, _("Cryptocurrency")),
        (PAYMENT_ONLINE, _("Online on website")),
    ]

    date = models.DateField(verbose_name=_("Date"))
    time_start = models.TimeField(null=True, blank=True, verbose_name=_("Time start"))
    time_end = models.TimeField(null=True, blank=True, verbose_name=_("Time end"))
    when_ready = models.BooleanField(default=False, verbose_name=_("When ready"))
    contact = models.TextField(verbose_name=_("Contact"))
    nickname = models.CharField(max_length=100, blank=True, verbose_name=_("Nickname"))
    phones = models.JSONField(default=list, verbose_name=_("Phones"))
    delivery_address = models.TextField(blank=True, verbose_name=_("Delivery address"))
    delivery_distance_meters = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Delivery distance meters"),
    )
    delivery_duration_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Delivery duration seconds"),
    )
    delivery_route_computed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Delivery route computed at"),
    )
    fulfillment_type = models.CharField(
        max_length=10,
        choices=FULFILLMENT_CHOICES,
        default=FULFILLMENT_DELIVERY,
        verbose_name=_("Fulfillment type"),
    )
    STATUS_UNCONFIRMED = "unconfirmed"
    STATUS_NEW = "new"
    STATUS_IN_WORK = "in_work"
    STATUS_READY = "ready"
    STATUS_CLIENT_APPROVED = "client_approved"
    STATUS_IN_DELIVERY = "in_delivery"
    STATUS_DELIVERED = "delivered"
    STATUS_CHOICES = [
        (STATUS_UNCONFIRMED, _("Unconfirmed")),
        (STATUS_NEW, _("New")),
        (STATUS_IN_WORK, _("In work")),
        (STATUS_READY, _("Ready")),
        (STATUS_CLIENT_APPROVED, _("Client approved")),
        (STATUS_IN_DELIVERY, _("In delivery")),
        (STATUS_DELIVERED, _("Delivered")),
    ]
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
        verbose_name=_("Status"),
    )
    taken_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_orders_taken",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Taken by"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_orders_created",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Created by"),
    )
    delivered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_orders_delivered",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Delivered by"),
    )
    weight = models.CharField(max_length=50, verbose_name=_("Weight"))
    filling = models.CharField(max_length=255, verbose_name=_("Filling"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    internal_description = models.TextField(blank=True, verbose_name=_("Internal description"))
    cake_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Cake price"))
    prepayment = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Prepayment"))
    is_paid = models.BooleanField(default=False, verbose_name=_("Is paid"))
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default=PAYMENT_UNKNOWN,
        verbose_name=_("Payment type"),
    )
    payment_date = models.DateField(null=True, blank=True, verbose_name=_("Payment date"))
    website_order = models.OneToOneField(
        "orders.Order",
        related_name="crm_order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Website order"),
    )
    flowwow_order_id = models.IntegerField(unique=True, null=True, blank=True, verbose_name=_("Flowwow order id"))
    flowwow_synced_description = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Flowwow synced description"),
    )
    flowwow_synced_internal_description = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Flowwow synced internal description"),
    )
    deleted = models.BooleanField(default=False, verbose_name=_("Deleted"))
    client_token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False,
        default=generate_crm_client_token,
        verbose_name=_("Client token"),
    )
    telegram_message_id = models.BigIntegerField(null=True, blank=True, verbose_name=_("Telegram message id"))
    telegram_media_ids = models.JSONField(default=list, verbose_name=_("Telegram media ids"))
    telegram_payload_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name=_("Telegram payload hash"),
    )
    telegram_posted_date = models.DateField(null=True, blank=True, verbose_name=_("Telegram posted date"))
    telegram_posted_time_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("Telegram posted time start"),
    )
    telegram_posted_time_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("Telegram posted time end"),
    )
    telegram_posted_when_ready = models.BooleanField(default=False, verbose_name=_("Telegram posted when ready"))
    telegram_posted_delivery_address = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Telegram posted delivery address"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("CRM order")
        verbose_name_plural = _("CRM orders")
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
        (ACTION_CREATED, _("Created")),
        (ACTION_UPDATED, _("Updated")),
        (ACTION_DELETED, _("Deleted")),
    ]

    SOURCE_CRM = "crm"
    SOURCE_ADMIN = "admin"
    SOURCE_WEBSITE = "website"
    SOURCE_FLOWWOW = "flowwow"
    SOURCE_CHOICES = [
        (SOURCE_CRM, _("CRM")),
        (SOURCE_ADMIN, _("Admin")),
        (SOURCE_WEBSITE, _("Website")),
        (SOURCE_FLOWWOW, _("Flowwow")),
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
    number = models.CharField(max_length=15, unique=True, verbose_name=_("Number"))
    resolved = models.BooleanField(verbose_name=_("Resolved"))
    user_id = models.BigIntegerField(null=True, blank=True, verbose_name=_("User ID"))
    username = models.CharField(max_length=32, blank=True, default="", verbose_name=_("Username"))
    checked_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Checked at"))

    class Meta:
        verbose_name = _("Resolved Telegram phone")
        verbose_name_plural = _("Resolved Telegram phones")

    def __str__(self) -> str:
        return self.number


class CrmOrderImage(models.Model):
    order = models.ForeignKey(CrmOrder, related_name="images", on_delete=models.CASCADE, verbose_name=_("Order"))
    image = models.ImageField(upload_to="crm_orders/", verbose_name=_("Image"))
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))
    source_url = models.TextField(null=True, blank=True, verbose_name=_("Source URL"))

    class Meta:
        ordering = ["position", "id"]
        verbose_name = _("CRM order image")
        verbose_name_plural = _("CRM order images")
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
        (KIND_BANK, _("Bank")),
        (KIND_CASH, _("Cash")),
        (KIND_CRYPTO, _("Crypto")),
        (KIND_VIRTUAL, _("Virtual")),
    ]

    name = models.CharField(max_length=100, verbose_name=_("Name"))
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, verbose_name=_("Kind"))
    bank_name = models.CharField(max_length=100, blank=True, verbose_name=_("Bank name"))
    iban = models.CharField(max_length=34, blank=True, verbose_name=_("IBAN"))
    currency = models.CharField(max_length=3, default="GEL", verbose_name=_("Currency"))

    class Meta:
        verbose_name = _("Financial account")
        verbose_name_plural = _("Financial accounts")

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
        (KIND_INCOME, _("Income")),
        (KIND_EXPENSE, _("Expense")),
        (KIND_TRANSFER, _("Transfer")),
        (KIND_WITHDRAWAL, _("Withdrawal")),
        (KIND_INVESTMENT, _("Investment")),
        (KIND_CORRECTION, _("Correction")),
        (KIND_OTHER, _("Other")),
    ]

    EXPENSE_SALARY = "salary"
    EXPENSE_RENT = "rent"
    EXPENSE_PRODUCTS = "products"
    EXPENSE_CONSUMABLES = "consumables"
    EXPENSE_EQUIPMENT = "equipment"
    EXPENSE_FEES = "fees"
    EXPENSE_TYPE_CHOICES = [
        (EXPENSE_SALARY, _("Salary")),
        (EXPENSE_RENT, _("Rent")),
        (EXPENSE_PRODUCTS, pgettext_lazy("expense type", "Products")),
        (EXPENSE_CONSUMABLES, _("Consumables")),
        (EXPENSE_EQUIPMENT, _("Equipment")),
        (EXPENSE_FEES, _("Fees")),
    ]

    INCOME_ONLINE = "online"
    INCOME_TERMINAL = "terminal"
    INCOME_CASH = "cash"
    INCOME_TRANSFER = "transfer"
    INCOME_TYPE_CHOICES = [
        (INCOME_ONLINE, _("Online")),
        (INCOME_TERMINAL, _("Terminal")),
        (INCOME_CASH, _("Cash")),
        (INCOME_TRANSFER, _("Transfer")),
    ]

    account = models.ForeignKey(
        FinancialAccount,
        related_name="transactions",
        on_delete=models.PROTECT,
        verbose_name=_("Account"),
    )
    date = models.DateField(verbose_name=_("Date"))
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Amount"))
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, verbose_name=_("Kind"))
    expense_type = models.CharField(
        max_length=20,
        choices=EXPENSE_TYPE_CHOICES,
        blank=True,
        verbose_name=_("Expense type"),
    )
    income_type = models.CharField(
        max_length=20,
        choices=INCOME_TYPE_CHOICES,
        blank=True,
        verbose_name=_("Income type"),
    )
    transfer_id = models.UUIDField(null=True, blank=True, verbose_name=_("Transfer id"))
    counterparty_name = models.CharField(max_length=255, blank=True, verbose_name=_("Counterparty name"))
    counterparty_iban = models.CharField(max_length=34, blank=True, verbose_name=_("Counterparty IBAN"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    external_id = models.CharField(max_length=512, blank=True, verbose_name=_("External id"))
    crm_orders = models.ManyToManyField(
        CrmOrder,
        related_name="financial_transactions",
        blank=True,
        verbose_name=_("CRM orders"),
    )
    matched_transaction = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Matched transaction"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("Financial transaction")
        verbose_name_plural = _("Financial transactions")
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


class FinancialTransactionRule(models.Model):
    OPERATOR_AND = "and"
    OPERATOR_OR = "or"
    OPERATOR_CHOICES = [
        (OPERATOR_AND, _("And")),
        (OPERATOR_OR, _("Or")),
    ]

    name = models.CharField(max_length=255, verbose_name=_("Name"))
    expense_type = models.CharField(
        max_length=20,
        choices=FinancialTransaction.EXPENSE_TYPE_CHOICES,
        verbose_name=_("Expense type"),
    )
    priority = models.IntegerField(verbose_name=_("Priority"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    operator = models.CharField(max_length=3, choices=OPERATOR_CHOICES, verbose_name=_("Operator"))

    class Meta:
        verbose_name = _("Financial transaction rule")
        verbose_name_plural = _("Financial transaction rules")
        ordering = ["priority", "id"]

    def __str__(self) -> str:
        return self.name


class FinancialTransactionRuleCondition(models.Model):
    FIELD_ACCOUNT_IBAN = "account_iban"
    FIELD_COUNTERPARTY_IBAN = "counterparty_iban"
    FIELD_COUNTERPARTY_NAME = "counterparty_name"
    FIELD_DESCRIPTION = "description"
    FIELD_CHOICES = [
        (FIELD_ACCOUNT_IBAN, _("Account IBAN")),
        (FIELD_COUNTERPARTY_IBAN, _("Counterparty IBAN")),
        (FIELD_COUNTERPARTY_NAME, _("Counterparty name")),
        (FIELD_DESCRIPTION, _("Description")),
    ]

    rule = models.ForeignKey(
        FinancialTransactionRule,
        related_name="conditions",
        on_delete=models.CASCADE,
        verbose_name=_("Rule"),
    )
    field = models.CharField(max_length=32, choices=FIELD_CHOICES, verbose_name=_("Field"))
    pattern = models.CharField(max_length=512, verbose_name=_("Pattern"))

    class Meta:
        verbose_name = _("Financial transaction rule condition")
        verbose_name_plural = _("Financial transaction rule conditions")
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.field} {self.pattern}"


class WhatsAppNumberCheck(CrmOrder):
    class Meta:
        proxy = True
        verbose_name = _("WhatsApp number check")
        verbose_name_plural = _("WhatsApp number check")


class WhatsAppGetNewQr(CrmOrder):
    class Meta:
        proxy = True
        verbose_name = _("WhatsApp get new QR")
        verbose_name_plural = _("WhatsApp get new QR")


class TelegramNumberCheck(CrmOrder):
    class Meta:
        proxy = True
        verbose_name = _("Telegram number check")
        verbose_name_plural = _("Telegram number check")
