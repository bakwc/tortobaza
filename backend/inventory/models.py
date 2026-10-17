from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from menu.models import ComponentRef


class Supplier(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name=_("Name"))
    phone = models.CharField(max_length=64, blank=True, verbose_name=_("Phone"))
    comment = models.TextField(blank=True, verbose_name=_("Comment"))

    class Meta:
        ordering = ["name"]
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")

    def __str__(self) -> str:
        return self.name


class Supply(models.Model):
    date = models.DateField(verbose_name=_("Date"))
    supplier = models.ForeignKey(
        Supplier,
        related_name="supplies",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Supplier"),
    )
    financial_transaction = models.OneToOneField(
        "crm.FinancialTransaction",
        related_name="supply",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Bank transaction"),
    )
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="+",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Created by"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = _("Supply")
        verbose_name_plural = _("Supplies")

    def __str__(self) -> str:
        return f"{self.date} #{self.pk}"


class SupplyReceipt(models.Model):
    supply = models.ForeignKey(
        Supply,
        related_name="receipts",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Supply"),
    )
    image = models.ImageField(upload_to="supply_receipts/", verbose_name=_("Image"))
    recognized = models.JSONField(verbose_name=_("Recognized"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        ordering = ["id"]
        verbose_name = _("Supply receipt")
        verbose_name_plural = _("Supply receipts")


class SupplyLine(models.Model):
    supply = models.ForeignKey(
        Supply,
        related_name="lines",
        on_delete=models.CASCADE,
        verbose_name=_("Supply"),
    )
    ingredient = models.ForeignKey(
        "menu.Ingredient",
        related_name="supply_lines",
        on_delete=models.PROTECT,
        verbose_name=_("Ingredient"),
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name=_("Quantity"))
    total = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Total"))

    class Meta:
        ordering = ["id"]
        verbose_name = _("Supply line")
        verbose_name_plural = _("Supply lines")


class Production(models.Model):
    date = models.DateField(verbose_name=_("Date"))
    semi_product = models.ForeignKey(
        "menu.SemiProduct",
        related_name="productions",
        on_delete=models.PROTECT,
        verbose_name=_("Semi-product"),
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name=_("Quantity"))
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="+",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Created by"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = _("Production")
        verbose_name_plural = _("Productions")

    def __str__(self) -> str:
        return f"{self.date} {self.semi_product}"


class WriteOffReason(models.Model):
    name = models.CharField(max_length=120, unique=True, verbose_name=_("Name"))

    class Meta:
        ordering = ["name"]
        verbose_name = _("Write-off reason")
        verbose_name_plural = _("Write-off reasons")

    def __str__(self) -> str:
        return self.name


class WriteOff(models.Model):
    date = models.DateField(verbose_name=_("Date"))
    reason = models.ForeignKey(
        WriteOffReason,
        related_name="write_offs",
        on_delete=models.PROTECT,
        verbose_name=_("Reason"),
    )
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="+",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Created by"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = _("Write-off")
        verbose_name_plural = _("Write-offs")

    def __str__(self) -> str:
        return f"{self.date} {self.reason}"


class WriteOffLine(ComponentRef):
    write_off = models.ForeignKey(
        WriteOff,
        related_name="lines",
        on_delete=models.CASCADE,
        verbose_name=_("Write-off"),
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name=_("Quantity"))

    class Meta(ComponentRef.Meta):
        ordering = ["id"]
        verbose_name = _("Write-off line")
        verbose_name_plural = _("Write-off lines")


class InventoryCount(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, _("Draft")),
        (STATUS_CLOSED, _("Closed")),
    ]

    date = models.DateField(verbose_name=_("Date"))
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name=_("Status"),
    )
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="+",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Created by"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Closed at"))

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = _("Inventory count")
        verbose_name_plural = _("Inventory counts")

    def __str__(self) -> str:
        return f"{self.date} #{self.pk}"


class InventoryCountLine(ComponentRef):
    count = models.ForeignKey(
        InventoryCount,
        related_name="lines",
        on_delete=models.CASCADE,
        verbose_name=_("Inventory count"),
    )
    actual_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name=_("Actual quantity"),
    )
    unit_cost = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("Unit cost"),
    )
    expected_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_("Expected quantity"),
    )

    class Meta(ComponentRef.Meta):
        ordering = ["id"]
        verbose_name = _("Inventory count line")
        verbose_name_plural = _("Inventory count lines")


class StockMovement(ComponentRef):
    KIND_SUPPLY = "supply"
    KIND_PRODUCTION_IN = "production_in"
    KIND_PRODUCTION_OUT = "production_out"
    KIND_ORDER = "order"
    KIND_WRITE_OFF = "write_off"
    KIND_INVENTORY = "inventory"
    KIND_CHOICES = [
        (KIND_SUPPLY, _("Supply")),
        (KIND_PRODUCTION_IN, _("Production output")),
        (KIND_PRODUCTION_OUT, _("Production consumption")),
        (KIND_ORDER, _("Order")),
        (KIND_WRITE_OFF, _("Write-off")),
        (KIND_INVENTORY, _("Inventory count")),
    ]

    date = models.DateField(verbose_name=_("Date"))
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, verbose_name=_("Kind"))
    quantity = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Quantity"))
    unit_cost = models.DecimalField(max_digits=14, decimal_places=6, verbose_name=_("Unit cost"))
    supply_line = models.ForeignKey(
        SupplyLine,
        related_name="movements",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Supply line"),
    )
    production = models.ForeignKey(
        Production,
        related_name="movements",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Production"),
    )
    crm_order = models.ForeignKey(
        "crm.CrmOrder",
        related_name="stock_movements",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("CRM order"),
    )
    write_off_line = models.ForeignKey(
        WriteOffLine,
        related_name="movements",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Write-off line"),
    )
    inventory_count_line = models.ForeignKey(
        InventoryCountLine,
        related_name="movements",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Inventory count line"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta(ComponentRef.Meta):
        ordering = ["date", "id"]
        verbose_name = _("Stock movement")
        verbose_name_plural = _("Stock movements")
