from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

DELIVERY_SCHEDULE_ALL_DAY = "all_day"
DELIVERY_SCHEDULE_SAME_DAY = "same_day"
DELIVERY_SCHEDULE_NEXT_DAY = "next_day"
DELIVERY_SCHEDULE_PLUS_2 = "plus_2"
DELIVERY_SCHEDULE_PLUS_3 = "plus_3"
DELIVERY_SCHEDULE_TIER_CHOICES = [
    (DELIVERY_SCHEDULE_ALL_DAY, _("All day")),
    (DELIVERY_SCHEDULE_SAME_DAY, _("Same day or later")),
    (DELIVERY_SCHEDULE_NEXT_DAY, _("Next day or later")),
    (DELIVERY_SCHEDULE_PLUS_2, _("Two days or later")),
    (DELIVERY_SCHEDULE_PLUS_3, _("Three days or later")),
]


class Category(models.Model):
    name = models.CharField(max_length=120, verbose_name=_("Name"))
    slug = models.SlugField(max_length=140, unique=True, verbose_name=_("Slug"))
    page_slug = models.SlugField(max_length=140, blank=True, verbose_name=_("Page slug"))
    page_heading = models.CharField(max_length=200, blank=True, verbose_name=_("Page heading"))
    page_description = models.TextField(blank=True, verbose_name=_("Page description"))
    seo_title = models.CharField(max_length=200, blank=True, verbose_name=_("SEO title"))
    seo_description = models.TextField(blank=True, verbose_name=_("SEO description"))
    image = models.ImageField(upload_to="categories/", blank=True, verbose_name=_("Image"))
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    delivery_schedule_tier = models.CharField(
        max_length=20,
        choices=DELIVERY_SCHEDULE_TIER_CHOICES,
        default=DELIVERY_SCHEDULE_SAME_DAY,
        verbose_name=_("Delivery schedule tier"),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        ordering = ["position", "name"]
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        constraints = [
            models.UniqueConstraint(
                fields=["page_slug_en"],
                condition=~models.Q(page_slug_en=""),
                name="uniq_category_page_slug_en",
            ),
            models.UniqueConstraint(
                fields=["page_slug_ka"],
                condition=~models.Q(page_slug_ka=""),
                name="uniq_category_page_slug_ka",
            ),
            models.UniqueConstraint(
                fields=["page_slug_ru"],
                condition=~models.Q(page_slug_ru=""),
                name="uniq_category_page_slug_ru",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        page_slugs = {
            slug
            for slug in (self.page_slug_en, self.page_slug_ka, self.page_slug_ru)
            if slug
        }
        if not page_slugs:
            return
        conflicts = Category.objects.exclude(pk=self.pk).filter(
            models.Q(page_slug_en__in=page_slugs)
            | models.Q(page_slug_ka__in=page_slugs)
            | models.Q(page_slug_ru__in=page_slugs)
        )
        if conflicts.exists():
            raise ValidationError(_("Page slugs must be unique across all languages."))
        landing_conflicts = CategoryLanding.objects.filter(
            models.Q(page_slug_en__in=page_slugs)
            | models.Q(page_slug_ka__in=page_slugs)
            | models.Q(page_slug_ru__in=page_slugs)
        )
        if landing_conflicts.exists():
            raise ValidationError(_("Page slugs must not collide with existing category landings."))


class CategoryLanding(models.Model):
    slug = models.SlugField(max_length=140, unique=True, verbose_name=_("Slug"))
    source = models.ForeignKey(
        Category,
        related_name="landings",
        on_delete=models.CASCADE,
        verbose_name=_("Source"),
    )
    page_slug = models.SlugField(max_length=140, blank=True, verbose_name=_("Page slug"))
    page_heading = models.CharField(max_length=200, blank=True, verbose_name=_("Page heading"))
    page_description = models.TextField(blank=True, verbose_name=_("Page description"))
    seo_title = models.CharField(max_length=200, blank=True, verbose_name=_("SEO title"))
    seo_description = models.TextField(blank=True, verbose_name=_("SEO description"))
    image = models.ImageField(upload_to="category_landings/", blank=True, verbose_name=_("Image"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        ordering = ["slug"]
        verbose_name = _("Category landing")
        verbose_name_plural = _("Category landings")
        constraints = [
            models.UniqueConstraint(
                fields=["page_slug_en"],
                condition=~models.Q(page_slug_en=""),
                name="uniq_category_landing_page_slug_en",
            ),
            models.UniqueConstraint(
                fields=["page_slug_ka"],
                condition=~models.Q(page_slug_ka=""),
                name="uniq_category_landing_page_slug_ka",
            ),
            models.UniqueConstraint(
                fields=["page_slug_ru"],
                condition=~models.Q(page_slug_ru=""),
                name="uniq_category_landing_page_slug_ru",
            ),
        ]

    def __str__(self) -> str:
        return self.slug

    def clean(self) -> None:
        page_slugs = {
            slug
            for slug in (self.page_slug_en, self.page_slug_ka, self.page_slug_ru)
            if slug
        }
        if not page_slugs:
            return
        conflicts = CategoryLanding.objects.exclude(pk=self.pk).filter(
            models.Q(page_slug_en__in=page_slugs)
            | models.Q(page_slug_ka__in=page_slugs)
            | models.Q(page_slug_ru__in=page_slugs)
        )
        if conflicts.exists():
            raise ValidationError(_("Page slugs must be unique across all languages."))
        category_conflicts = Category.objects.filter(
            models.Q(page_slug_en__in=page_slugs)
            | models.Q(page_slug_ka__in=page_slugs)
            | models.Q(page_slug_ru__in=page_slugs)
        )
        if category_conflicts.exists():
            raise ValidationError(_("Page slugs must not collide with existing categories."))


class OptionGroup(models.Model):
    SELECTION_SINGLE = "single"
    SELECTION_MULTI = "multi"
    SELECTION_CHOICES = [
        (SELECTION_SINGLE, _("Single")),
        (SELECTION_MULTI, _("Multi")),
    ]

    name = models.CharField(max_length=120, verbose_name=_("Name"))
    slug = models.SlugField(max_length=140, unique=True, verbose_name=_("Slug"))
    selection_type = models.CharField(
        max_length=10,
        choices=SELECTION_CHOICES,
        default=SELECTION_SINGLE,
        verbose_name=_("Selection type"),
    )
    is_required_default = models.BooleanField(default=True, verbose_name=_("Required by default"))
    min_selections = models.PositiveIntegerField(default=0, verbose_name=_("Minimum selections"))
    max_selections = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Maximum selections"),
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("Option group")
        verbose_name_plural = _("Option groups")

    def __str__(self) -> str:
        return self.name


class Option(models.Model):
    group = models.ForeignKey(
        OptionGroup,
        related_name="options",
        on_delete=models.CASCADE,
        verbose_name=_("Group"),
    )
    name = models.CharField(max_length=120, verbose_name=_("Name"))
    image = models.ImageField(upload_to="options/", blank=True, verbose_name=_("Image"))
    price_delta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Price delta"),
    )
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    class Meta:
        ordering = ["position", "name"]
        verbose_name = _("Option")
        verbose_name_plural = _("Options")

    def __str__(self) -> str:
        return f"{self.group.name}: {self.name}"


class Product(models.Model):
    DELIVERY_SCHEDULE_ALL_DAY = DELIVERY_SCHEDULE_ALL_DAY
    DELIVERY_SCHEDULE_SAME_DAY = DELIVERY_SCHEDULE_SAME_DAY
    DELIVERY_SCHEDULE_NEXT_DAY = DELIVERY_SCHEDULE_NEXT_DAY
    DELIVERY_SCHEDULE_PLUS_2 = DELIVERY_SCHEDULE_PLUS_2
    DELIVERY_SCHEDULE_PLUS_3 = DELIVERY_SCHEDULE_PLUS_3
    DELIVERY_SCHEDULE_TIER_CHOICES = DELIVERY_SCHEDULE_TIER_CHOICES

    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.PROTECT,
        verbose_name=_("Category"),
    )
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    slug = models.SlugField(max_length=220, unique=True, verbose_name=_("Slug"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    base_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Base price"))
    delivery_schedule_tier = models.CharField(
        max_length=20,
        choices=DELIVERY_SCHEDULE_TIER_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Delivery schedule tier"),
    )
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    option_groups = models.ManyToManyField(
        OptionGroup,
        through="ProductOptionGroup",
        related_name="products",
        verbose_name=_("Option groups"),
    )

    class Meta:
        ordering = ["position", "-created_at"]
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self) -> str:
        return self.name

    @property
    def effective_delivery_schedule_tier(self) -> str:
        if self.delivery_schedule_tier is None:
            return self.category.delivery_schedule_tier
        return self.delivery_schedule_tier


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        related_name="images",
        on_delete=models.CASCADE,
        verbose_name=_("Product"),
    )
    image = models.ImageField(upload_to="products/", verbose_name=_("Image"))
    alt = models.CharField(max_length=200, blank=True, verbose_name=_("Alt text"))
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))

    class Meta:
        ordering = ["position", "id"]
        verbose_name = _("Product image")
        verbose_name_plural = _("Product images")

    def __str__(self) -> str:
        return f"{self.product.name} image #{self.pk}"


class ProductOptionGroup(models.Model):
    product = models.ForeignKey(
        Product,
        related_name="product_option_groups",
        on_delete=models.CASCADE,
        verbose_name=_("Product"),
    )
    option_group = models.ForeignKey(
        OptionGroup,
        related_name="product_links",
        on_delete=models.PROTECT,
        verbose_name=_("Option group"),
    )
    position = models.PositiveIntegerField(default=0, verbose_name=_("Position"))
    is_required = models.BooleanField(null=True, blank=True, verbose_name=_("Is required"))

    class Meta:
        ordering = ["position", "id"]
        verbose_name = _("Product option group")
        verbose_name_plural = _("Product option groups")
        constraints = [
            models.UniqueConstraint(fields=["product", "option_group"], name="uniq_product_option_group"),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} - {self.option_group.name}"

    @property
    def effective_is_required(self) -> bool:
        if self.is_required is None:
            return self.option_group.is_required_default
        return self.is_required

    @property
    def effective_min_selections(self) -> int:
        group = self.option_group
        if group.selection_type == OptionGroup.SELECTION_SINGLE:
            return 1 if self.effective_is_required else 0
        if self.effective_is_required and group.min_selections < 1:
            return 1
        return group.min_selections

    @property
    def effective_max_selections(self) -> int | None:
        group = self.option_group
        if group.selection_type == OptionGroup.SELECTION_SINGLE:
            return 1
        return group.max_selections
