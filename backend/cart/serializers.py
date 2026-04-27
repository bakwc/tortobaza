from collections import defaultdict

from django.conf import settings
from rest_framework import serializers

from cart.models import Cart, CartItem, CartItemOption
from catalog.models import Option, Product, ProductOptionGroup


class CartItemOptionReadSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="option.id")
    name = serializers.CharField(source="option.name")
    price_delta = serializers.DecimalField(source="option.price_delta", max_digits=10, decimal_places=2)
    group_id = serializers.IntegerField(source="option.group_id")
    group_name = serializers.CharField(source="option.group.name")

    class Meta:
        model = CartItemOption
        fields = ["id", "name", "price_delta", "group_id", "group_name"]


class CartItemProductSerializer(serializers.ModelSerializer):
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "slug", "name", "base_price", "primary_image"]

    def get_primary_image(self, obj: Product):
        first = obj.images.order_by("position", "id").first()
        if first is None:
            return None
        url = first.image.url
        return f"{settings.PUBLIC_BASE_URL.rstrip('/')}/{url.lstrip('/')}"


class CartItemReadSerializer(serializers.ModelSerializer):
    product = CartItemProductSerializer(read_only=True)
    options = CartItemOptionReadSerializer(many=True, read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "comment", "options", "unit_price", "line_total", "added_at"]


class CartReadSerializer(serializers.ModelSerializer):
    items = CartItemReadSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ["token", "items", "subtotal", "created_at", "updated_at"]


def _validate_options_for_product(product: Product, option_ids: list[int]) -> list[Option]:
    if not option_ids:
        options: list[Option] = []
    else:
        options = list(
            Option.objects.filter(id__in=option_ids, is_active=True).select_related("group")
        )
        if len(options) != len(set(option_ids)):
            raise serializers.ValidationError({"option_ids": "Some options are invalid or inactive."})

    links = list(
        ProductOptionGroup.objects.filter(product=product).select_related("option_group")
    )
    allowed_group_ids = {link.option_group_id for link in links}

    for option in options:
        if option.group_id not in allowed_group_ids:
            raise serializers.ValidationError(
                {"option_ids": f"Option '{option.name}' does not belong to this product."}
            )

    selected_by_group: dict[int, list[Option]] = defaultdict(list)
    for option in options:
        selected_by_group[option.group_id].append(option)

    for link in links:
        group = link.option_group
        chosen = selected_by_group.get(group.id, [])
        required = link.effective_is_required
        if required and len(chosen) == 0:
            raise serializers.ValidationError(
                {"option_ids": f"Option group '{group.name}' is required."}
            )
        if group.selection_type == group.SELECTION_SINGLE and len(chosen) > 1:
            raise serializers.ValidationError(
                {"option_ids": f"Option group '{group.name}' allows only one option."}
            )

    return options


class CartItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    option_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        product = Product.objects.filter(id=attrs["product_id"], is_active=True).first()
        if product is None:
            raise serializers.ValidationError({"product_id": "Product not found."})
        attrs["product"] = product
        attrs["options"] = _validate_options_for_product(product, attrs.get("option_ids", []))
        return attrs


class CartItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, required=False)
    option_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        cart_item: CartItem = self.context["cart_item"]
        if "option_ids" in attrs:
            attrs["options"] = _validate_options_for_product(cart_item.product, attrs["option_ids"])
        return attrs
