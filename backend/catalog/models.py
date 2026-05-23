from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "name"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name


class OptionGroup(models.Model):
    SELECTION_SINGLE = "single"
    SELECTION_MULTI = "multi"
    SELECTION_CHOICES = [
        (SELECTION_SINGLE, "Single"),
        (SELECTION_MULTI, "Multi"),
    ]

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    selection_type = models.CharField(max_length=10, choices=SELECTION_CHOICES, default=SELECTION_SINGLE)
    is_required_default = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Option(models.Model):
    group = models.ForeignKey(OptionGroup, related_name="options", on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    image = models.ImageField(upload_to="options/", blank=True)
    price_delta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "name"]

    def __str__(self) -> str:
        return f"{self.group.name}: {self.name}"


class Product(models.Model):
    DELIVERY_SCHEDULE_SAME_DAY = "same_day"
    DELIVERY_SCHEDULE_NEXT_DAY = "next_day"
    DELIVERY_SCHEDULE_PLUS_2 = "plus_2"
    DELIVERY_SCHEDULE_PLUS_3 = "plus_3"
    DELIVERY_SCHEDULE_TIER_CHOICES = [
        (DELIVERY_SCHEDULE_SAME_DAY, "Same day or later"),
        (DELIVERY_SCHEDULE_NEXT_DAY, "Next day or later"),
        (DELIVERY_SCHEDULE_PLUS_2, "Two days or later"),
        (DELIVERY_SCHEDULE_PLUS_3, "Three days or later"),
    ]

    category = models.ForeignKey(Category, related_name="products", on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_schedule_tier = models.CharField(
        max_length=20,
        choices=DELIVERY_SCHEDULE_TIER_CHOICES,
        default=DELIVERY_SCHEDULE_SAME_DAY,
    )
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    option_groups = models.ManyToManyField(OptionGroup, through="ProductOptionGroup", related_name="products")

    class Meta:
        ordering = ["position", "-created_at"]

    def __str__(self) -> str:
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/")
    alt = models.CharField(max_length=200, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"{self.product.name} image #{self.pk}"


class ProductOptionGroup(models.Model):
    product = models.ForeignKey(Product, related_name="product_option_groups", on_delete=models.CASCADE)
    option_group = models.ForeignKey(OptionGroup, related_name="product_links", on_delete=models.PROTECT)
    position = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ["position", "id"]
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
