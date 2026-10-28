from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from menu.models import UNIT_PIECE, ComponentRef, Ingredient, SemiProduct


class Supplier(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name=_("Name"))
    tin = models.CharField(max_length=32, unique=True, null=True, blank=True, verbose_name=_("TIN"))
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
    waybill = models.OneToOneField(
        "rsge.Waybill",
        related_name="supply",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Waybill"),
    )
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


class WaybillIngredientAlias(models.Model):
    seller_tin = models.CharField(max_length=32, verbose_name=_("Seller TIN"))
    bar_code = models.CharField(max_length=128, blank=True, verbose_name=_("Barcode"))
    name = models.TextField(verbose_name=_("Name"))
    unit_txt = models.CharField(max_length=64, blank=True, verbose_name=_("Unit"))
    ingredient = models.ForeignKey(
        "menu.Ingredient",
        related_name="waybill_aliases",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Ingredient"),
    )
    factor = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("Factor"),
    )
    ignored = models.BooleanField(default=False, verbose_name=_("Ignored"))

    class Meta:
        verbose_name = _("Waybill ingredient alias")
        verbose_name_plural = _("Waybill ingredient aliases")
        constraints = [
            models.UniqueConstraint(
                fields=["seller_tin", "bar_code"],
                condition=~models.Q(bar_code=""),
                name="waybill_alias_seller_barcode",
            ),
            models.UniqueConstraint(
                fields=["seller_tin", "name", "unit_txt"],
                condition=models.Q(bar_code=""),
                name="waybill_alias_seller_name_unit",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(ignored=True, ingredient__isnull=True, factor__isnull=True)
                    | models.Q(ignored=False, ingredient__isnull=False, factor__isnull=False)
                ),
                name="waybill_alias_ignored_or_mapped",
            ),
        ]


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


class FinishedGood(models.Model):
    tech_card = models.ForeignKey(
        "menu.TechCard",
        related_name="finished_goods",
        on_delete=models.PROTECT,
        verbose_name=_("Tech card"),
    )
    weight_kg = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_("Weight, kg"),
    )
    signature = models.CharField(max_length=1000, unique=True, verbose_name=_("Signature"))
    avg_cost = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        default=Decimal("0"),
        verbose_name=_("Average cost"),
    )

    class Meta:
        ordering = ["tech_card__name", "id"]
        verbose_name = _("Finished good")
        verbose_name_plural = _("Finished goods")

    def __str__(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        parts = [self.tech_card.name]
        if self.weight_kg is not None:
            parts.append(f"{format(self.weight_kg, 'f')} kg")
        labels = []
        for row in sorted(self.modifiers.all(), key=lambda item: item.modifier_id):
            if row.quantity == 1:
                labels.append(row.modifier.name)
            else:
                labels.append(f"{row.modifier.name} ×{row.quantity}")
        if labels:
            parts.append(", ".join(labels))
        return " · ".join(parts)

    @property
    def unit(self) -> str:
        return UNIT_PIECE


class FinishedGoodModifier(models.Model):
    finished_good = models.ForeignKey(
        FinishedGood,
        related_name="modifiers",
        on_delete=models.CASCADE,
        verbose_name=_("Finished good"),
    )
    modifier = models.ForeignKey(
        "menu.Modifier",
        related_name="finished_goods",
        on_delete=models.PROTECT,
        verbose_name=_("Modifier"),
    )
    quantity = models.PositiveIntegerField(verbose_name=_("Quantity"))

    class Meta:
        ordering = ["modifier_id", "id"]
        verbose_name = _("Finished good modifier")
        verbose_name_plural = _("Finished good modifiers")


class FinishedProduction(models.Model):
    date = models.DateField(verbose_name=_("Date"))
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
        verbose_name = _("Finished production")
        verbose_name_plural = _("Finished productions")

    def __str__(self) -> str:
        return f"{self.date} #{self.pk}"


class FinishedProductionLine(models.Model):
    production = models.ForeignKey(
        FinishedProduction,
        related_name="lines",
        on_delete=models.CASCADE,
        verbose_name=_("Finished production"),
    )
    finished_good = models.ForeignKey(
        FinishedGood,
        related_name="production_lines",
        on_delete=models.PROTECT,
        verbose_name=_("Finished good"),
    )
    quantity = models.PositiveIntegerField(verbose_name=_("Quantity"))

    class Meta:
        ordering = ["id"]
        verbose_name = _("Finished production line")
        verbose_name_plural = _("Finished production lines")


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


class StockComponent(ComponentRef):
    finished_good = models.ForeignKey(
        FinishedGood,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Finished good"),
    )

    class Meta(ComponentRef.Meta):
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(ingredient__isnull=False, semi_product__isnull=True, finished_good__isnull=True)
                    | models.Q(ingredient__isnull=True, semi_product__isnull=False, finished_good__isnull=True)
                    | models.Q(ingredient__isnull=True, semi_product__isnull=True, finished_good__isnull=False)
                ),
                name="%(app_label)s_%(class)s_one_component",
            ),
        ]

    @property
    def component(self) -> Ingredient | SemiProduct | FinishedGood:
        if self.finished_good_id is not None:
            return self.finished_good
        if self.ingredient_id is not None:
            return self.ingredient
        return self.semi_product


class WriteOffLine(StockComponent):
    write_off = models.ForeignKey(
        WriteOff,
        related_name="lines",
        on_delete=models.CASCADE,
        verbose_name=_("Write-off"),
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name=_("Quantity"))

    class Meta(StockComponent.Meta):
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


class InventoryCountLine(StockComponent):
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

    class Meta(StockComponent.Meta):
        ordering = ["id"]
        verbose_name = _("Inventory count line")
        verbose_name_plural = _("Inventory count lines")


class StockMovement(StockComponent):
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
    finished_production_line = models.ForeignKey(
        FinishedProductionLine,
        related_name="movements",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Finished production line"),
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

    class Meta(StockComponent.Meta):
        ordering = ["date", "id"]
        verbose_name = _("Stock movement")
        verbose_name_plural = _("Stock movements")
