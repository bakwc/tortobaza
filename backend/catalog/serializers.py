from rest_framework import serializers

from catalog.models import (
    Category,
    CategoryLanding,
    Option,
    Product,
    ProductImage,
    ProductOptionGroup,
)
from catalog.responsive_urls import detail_image, list_primary_image


def category_page_slugs(obj: Category | CategoryLanding) -> dict[str, str]:
    return {
        "en": obj.page_slug_en or "",
        "ka": obj.page_slug_ka or "",
        "ru": obj.page_slug_ru or "",
    }


class CategorySerializer(serializers.ModelSerializer):
    page_slugs = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "slug",
            "page_slug",
            "name",
            "position",
            "delivery_schedule_tier",
            "page_slugs",
            "updated_at",
        ]

    def get_page_slugs(self, obj: Category) -> dict[str, str]:
        return category_page_slugs(obj)


class CategoryDetailSerializer(serializers.ModelSerializer):
    page_slugs = serializers.SerializerMethodField()
    source_page_slug = serializers.CharField(source="page_slug", read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "slug",
            "page_slug",
            "source_page_slug",
            "name",
            "page_heading",
            "page_description",
            "seo_title",
            "seo_description",
            "image",
            "position",
            "delivery_schedule_tier",
            "page_slugs",
            "updated_at",
        ]

    def get_page_slugs(self, obj: Category) -> dict[str, str]:
        return category_page_slugs(obj)

    def get_image(self, obj: Category):
        if not obj.image.name:
            return None
        public_base_url = self.context["request"].build_absolute_uri("/").rstrip("/")
        return list_primary_image(obj.image.name, public_base_url)


class CategoryLandingDetailSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(source="source.slug", read_only=True)
    source_page_slug = serializers.CharField(source="source.page_slug", read_only=True)
    name = serializers.CharField(source="source.name", read_only=True)
    position = serializers.IntegerField(source="source.position", read_only=True)
    delivery_schedule_tier = serializers.CharField(
        source="source.delivery_schedule_tier", read_only=True
    )
    page_slugs = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = CategoryLanding
        fields = [
            "id",
            "slug",
            "page_slug",
            "source_page_slug",
            "name",
            "page_heading",
            "page_description",
            "seo_title",
            "seo_description",
            "image",
            "position",
            "delivery_schedule_tier",
            "page_slugs",
            "updated_at",
        ]

    def get_page_slugs(self, obj: CategoryLanding) -> dict[str, str]:
        return category_page_slugs(obj)

    def get_image(self, obj: CategoryLanding):
        image_name = obj.image.name or obj.source.image.name
        if not image_name:
            return None
        public_base_url = self.context["request"].build_absolute_uri("/").rstrip("/")
        return list_primary_image(image_name, public_base_url)


class CategoryLandingListSerializer(serializers.ModelSerializer):
    page_slugs = serializers.SerializerMethodField()

    class Meta:
        model = CategoryLanding
        fields = [
            "id",
            "slug",
            "page_slug",
            "page_slugs",
            "updated_at",
        ]

    def get_page_slugs(self, obj: CategoryLanding) -> dict[str, str]:
        return category_page_slugs(obj)


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt", "position"]

    def get_image(self, obj: ProductImage) -> dict[str, str]:
        public_base_url = self.context["request"].build_absolute_uri("/").rstrip("/")
        return detail_image(obj.image.name, public_base_url)


class OptionSerializer(serializers.ModelSerializer):
    price_delta = serializers.DecimalField(max_digits=10, decimal_places=2)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Option
        fields = ["id", "name", "image", "price_delta", "position"]

    def get_image(self, obj: Option):
        if not obj.image.name:
            return None
        public_base_url = self.context["request"].build_absolute_uri("/").rstrip("/")
        return list_primary_image(obj.image.name, public_base_url)


class ProductOptionGroupSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="option_group.id")
    name = serializers.CharField(source="option_group.name")
    slug = serializers.CharField(source="option_group.slug")
    selection_type = serializers.CharField(source="option_group.selection_type")
    is_required = serializers.SerializerMethodField()
    min_selections = serializers.SerializerMethodField()
    max_selections = serializers.SerializerMethodField()
    options = serializers.SerializerMethodField()

    class Meta:
        model = ProductOptionGroup
        fields = [
            "id",
            "name",
            "slug",
            "selection_type",
            "is_required",
            "min_selections",
            "max_selections",
            "position",
            "options",
        ]

    def get_is_required(self, obj: ProductOptionGroup) -> bool:
        return obj.effective_is_required

    def get_min_selections(self, obj: ProductOptionGroup) -> int:
        return obj.effective_min_selections

    def get_max_selections(self, obj: ProductOptionGroup) -> int | None:
        return obj.effective_max_selections

    def get_options(self, obj: ProductOptionGroup):
        active = obj.option_group.options.filter(is_active=True)
        return OptionSerializer(active, many=True, context=self.context).data


class ProductListSerializer(serializers.ModelSerializer):
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    primary_image = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = ["id", "slug", "name", "base_price", "primary_image", "category"]

    def get_primary_image(self, obj: Product):
        first = obj.images.order_by("position", "id").first()
        if first is None:
            return None
        public_base_url = self.context["request"].build_absolute_uri("/").rstrip("/")
        return list_primary_image(first.image.name, public_base_url)


class ProductDetailSerializer(serializers.ModelSerializer):
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    option_groups = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "slug",
            "name",
            "description",
            "base_price",
            "category",
            "images",
            "option_groups",
        ]

    def get_option_groups(self, obj: Product):
        links = obj.product_option_groups.select_related("option_group").prefetch_related(
            "option_group__options"
        ).order_by("position", "id")
        return ProductOptionGroupSerializer(links, many=True, context=self.context).data
