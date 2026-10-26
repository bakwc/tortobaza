from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

UNIT_GRAM = "g"
UNIT_MILLILITER = "ml"
UNIT_PIECE = "pcs"
UNIT_CHOICES = [
    (UNIT_GRAM, _("Gram")),
    (UNIT_MILLILITER, _("Milliliter")),
    (UNIT_PIECE, _("Piece")),
]


class IngredientCategory(models.Model):
    name = models.CharField(max_length=120, unique=True, verbose_name=_("Name"))
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))

    class Meta:
        ordering = ["position", "name"]
        verbose_name = _("Ingredient category")
        verbose_name_plural = _("Ingredient categories")

    def __str__(self) -> str:
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name=_("Name"))
    category = models.ForeignKey(
        IngredientCategory,
        related_name="ingredients",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Category"),
    )
    unit = models.CharField(max_length=3, choices=UNIT_CHOICES, verbose_name=_("Unit"))
    avg_cost = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        default=Decimal("0"),
        verbose_name=_("Average cost"),
    )
    cost_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name=_("Cost quantity"),
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Sale price"),
    )
    grams_per_unit = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name=_("Grams per unit"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    class Meta:
        ordering = ["name"]
        verbose_name = _("Ingredient")
        verbose_name_plural = _("Ingredients")

    def __str__(self) -> str:
        return self.name


class SemiProduct(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name=_("Name"))
    unit = models.CharField(max_length=3, choices=UNIT_CHOICES, verbose_name=_("Unit"))
    yield_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name=_("Yield quantity"),
    )
    is_produced = models.BooleanField(default=False, verbose_name=_("Produced in advance"))
    avg_cost = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        default=Decimal("0"),
        verbose_name=_("Average cost"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    method = models.TextField(blank=True, default="", verbose_name=_("Method"))

    class Meta:
        ordering = ["name"]
        verbose_name = _("Semi-product")
        verbose_name_plural = _("Semi-products")

    def __str__(self) -> str:
        return self.name


class SemiProductImage(models.Model):
    semi_product = models.ForeignKey(
        SemiProduct,
        related_name="images",
        on_delete=models.CASCADE,
        verbose_name=_("Semi-product"),
    )
    image = models.ImageField(upload_to="semi_products/", verbose_name=_("Image"))
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))

    class Meta:
        ordering = ["position", "id"]
        verbose_name = _("Semi-product image")
        verbose_name_plural = _("Semi-product images")

    def __str__(self) -> str:
        return f"Image #{self.pk} for {self.semi_product_id}"


class ComponentRef(models.Model):
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Ingredient"),
    )
    semi_product = models.ForeignKey(
        SemiProduct,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Semi-product"),
    )

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(ingredient__isnull=False, semi_product__isnull=True)
                    | models.Q(ingredient__isnull=True, semi_product__isnull=False)
                ),
                name="%(app_label)s_%(class)s_one_component",
            ),
        ]

    @property
    def component(self) -> Ingredient | SemiProduct:
        if self.ingredient_id is not None:
            return self.ingredient
        return self.semi_product


LOSS_PERCENT_VALIDATORS = [
    MinValueValidator(Decimal("0")),
    MaxValueValidator(Decimal("99.99")),
]


class SemiProductLine(ComponentRef):
    parent = models.ForeignKey(
        SemiProduct,
        related_name="lines",
        on_delete=models.CASCADE,
        verbose_name=_("Semi-product"),
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name=_("Quantity"))
    quantity_unit = models.CharField(max_length=3, choices=UNIT_CHOICES, verbose_name=_("Quantity unit"))
    loss_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=LOSS_PERCENT_VALIDATORS,
        verbose_name=_("Loss percent"),
    )
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))

    class Meta(ComponentRef.Meta):
        ordering = ["position", "id"]
        verbose_name = _("Semi-product line")
        verbose_name_plural = _("Semi-product lines")


class ModifierGroup(models.Model):
    SELECTION_SINGLE = "single"
    SELECTION_MULTI = "multi"
    SELECTION_CHOICES = [
        (SELECTION_SINGLE, _("Single")),
        (SELECTION_MULTI, _("Multi")),
    ]

    name = models.CharField(max_length=120, unique=True, verbose_name=_("Name"))
    selection_type = models.CharField(
        max_length=10,
        choices=SELECTION_CHOICES,
        verbose_name=_("Selection type"),
    )
    is_required = models.BooleanField(default=False, verbose_name=_("Is required"))
    min_selections = models.PositiveIntegerField(default=0, verbose_name=_("Minimum selections"))
    max_selections = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Maximum selections"),
    )
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))

    class Meta:
        ordering = ["position", "name"]
        verbose_name = _("Modifier group")
        verbose_name_plural = _("Modifier groups")

    def __str__(self) -> str:
        return self.name


class Modifier(models.Model):
    group = models.ForeignKey(
        ModifierGroup,
        related_name="modifiers",
        on_delete=models.CASCADE,
        verbose_name=_("Group"),
    )
    name = models.CharField(max_length=120, verbose_name=_("Name"))
    catalog_option = models.OneToOneField(
        "catalog.Option",
        related_name="menu_modifier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Website option"),
    )
    ingredient = models.ForeignKey(
        Ingredient,
        related_name="default_for_modifiers",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Default ingredient"),
    )
    semi_product = models.ForeignKey(
        SemiProduct,
        related_name="default_for_modifiers",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Default semi-product"),
    )
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    class Meta:
        ordering = ["position", "name"]
        verbose_name = _("Modifier")
        verbose_name_plural = _("Modifiers")
        constraints = [
            models.UniqueConstraint(fields=["group", "name"], name="uniq_menu_modifier_group_name"),
            models.CheckConstraint(
                condition=models.Q(ingredient__isnull=True) | models.Q(semi_product__isnull=True),
                name="menu_modifier_one_default_component",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.group.name}: {self.name}"


class TechCardCategory(models.Model):
    name = models.CharField(max_length=120, unique=True, verbose_name=_("Name"))
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))

    class Meta:
        ordering = ["position", "name"]
        verbose_name = _("Tech card category")
        verbose_name_plural = _("Tech card categories")

    def __str__(self) -> str:
        return self.name


class TechCard(models.Model):
    KIND_WEIGHTED = "weighted"
    KIND_PIECE = "piece"
    KIND_CHOICES = [
        (KIND_WEIGHTED, _("Per kilogram")),
        (KIND_PIECE, _("Per piece")),
    ]

    name = models.CharField(max_length=200, unique=True, verbose_name=_("Name"))
    category = models.ForeignKey(
        TechCardCategory,
        related_name="tech_cards",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Category"),
    )
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, verbose_name=_("Kind"))
    basis_weight_kg = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name=_("Basis weight, kg"),
    )
    basis_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        verbose_name=_("Basis quantity"),
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Sale price"),
    )
    method = models.TextField(blank=True, default="", verbose_name=_("Method"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        ordering = ["name"]
        verbose_name = _("Tech card")
        verbose_name_plural = _("Tech cards")

    def __str__(self) -> str:
        return self.name


class TechCardImage(models.Model):
    tech_card = models.ForeignKey(
        TechCard,
        related_name="images",
        on_delete=models.CASCADE,
        verbose_name=_("Tech card"),
    )
    image = models.ImageField(upload_to="tech_cards/", verbose_name=_("Image"))
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))

    class Meta:
        ordering = ["position", "id"]
        verbose_name = _("Tech card image")
        verbose_name_plural = _("Tech card images")

    def __str__(self) -> str:
        return f"Image #{self.pk} for {self.tech_card_id}"


class TechCardSection(models.Model):
    tech_card = models.ForeignKey(
        TechCard,
        related_name="sections",
        on_delete=models.CASCADE,
        verbose_name=_("Tech card"),
    )
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    method = models.TextField(blank=True, default="", verbose_name=_("Method"))
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))

    class Meta:
        ordering = ["position", "id"]
        verbose_name = _("Tech card section")
        verbose_name_plural = _("Tech card sections")
        constraints = [
            models.UniqueConstraint(
                fields=["tech_card", "name"],
                name="uniq_menu_tech_card_section_name",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tech_card.name}: {self.name}"


class TechCardLine(ComponentRef):
    tech_card = models.ForeignKey(
        TechCard,
        related_name="lines",
        on_delete=models.CASCADE,
        verbose_name=_("Tech card"),
    )
    section = models.ForeignKey(
        TechCardSection,
        related_name="lines",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Section"),
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name=_("Quantity"))
    quantity_unit = models.CharField(max_length=3, choices=UNIT_CHOICES, verbose_name=_("Quantity unit"))
    loss_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=LOSS_PERCENT_VALIDATORS,
        verbose_name=_("Loss percent"),
    )
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))

    class Meta(ComponentRef.Meta):
        ordering = ["position", "id"]
        verbose_name = _("Tech card line")
        verbose_name_plural = _("Tech card lines")


class TechCardModifierGroup(models.Model):
    tech_card = models.ForeignKey(
        TechCard,
        related_name="modifier_groups",
        on_delete=models.CASCADE,
        verbose_name=_("Tech card"),
    )
    group = models.ForeignKey(
        ModifierGroup,
        related_name="tech_card_links",
        on_delete=models.PROTECT,
        verbose_name=_("Modifier group"),
    )
    is_required = models.BooleanField(null=True, blank=True, verbose_name=_("Is required"))
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))

    class Meta:
        ordering = ["position", "id"]
        verbose_name = _("Tech card modifier group")
        verbose_name_plural = _("Tech card modifier groups")
        constraints = [
            models.UniqueConstraint(
                fields=["tech_card", "group"],
                name="uniq_menu_tech_card_modifier_group",
            ),
        ]

    @property
    def effective_is_required(self) -> bool:
        if self.is_required is None:
            return self.group.is_required
        return self.is_required


class TechCardModifierLine(ComponentRef):
    tech_card = models.ForeignKey(
        TechCard,
        related_name="modifier_lines",
        on_delete=models.CASCADE,
        verbose_name=_("Tech card"),
    )
    modifier = models.ForeignKey(
        Modifier,
        related_name="tech_card_lines",
        on_delete=models.PROTECT,
        verbose_name=_("Modifier"),
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name=_("Quantity"))
    quantity_unit = models.CharField(max_length=3, choices=UNIT_CHOICES, verbose_name=_("Quantity unit"))
    loss_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=LOSS_PERCENT_VALIDATORS,
        verbose_name=_("Loss percent"),
    )
    scales_by_weight = models.BooleanField(default=True, verbose_name=_("Scales by weight"))
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))

    class Meta(ComponentRef.Meta):
        ordering = ["position", "id"]
        verbose_name = _("Tech card modifier line")
        verbose_name_plural = _("Tech card modifier lines")
