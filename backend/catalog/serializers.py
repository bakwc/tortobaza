from rest_framework import serializers

from catalog.models import (
    Category,
    Option,
    Product,
    ProductImage,
    ProductOptionGroup,
)
from catalog.responsive_urls import detail_image, list_primary_image


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "slug", "name", "position", "delivery_schedule_tier"]


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
    options = serializers.SerializerMethodField()

    class Meta:
        model = ProductOptionGroup
        fields = ["id", "name", "slug", "selection_type", "is_required", "position", "options"]

    def get_is_required(self, obj: ProductOptionGroup) -> bool:
        return obj.effective_is_required

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
