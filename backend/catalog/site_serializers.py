from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from PIL import Image, ImageOps
from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from catalog.crop import crop_tuple
from catalog.models import (
    Category,
    CategoryLanding,
    Option,
    OptionGroup,
    Product,
    ProductImage,
    ProductOptionGroup,
)
from catalog.auto_translate import KIND_FIELDS, LANGUAGES, schedule_translation
from catalog.responsive_urls import detail_image, list_primary_image
from menu.models import TechCard


def public_base_url(context: dict) -> str:
    return context["request"].build_absolute_uri("/").rstrip("/")


def image_dimensions(rel: str) -> tuple[int, int]:
    path = Path(settings.MEDIA_ROOT) / rel
    im = ImageOps.exif_transpose(Image.open(path))
    return im.size


def cropped_image_payload(
    context: dict,
    rel: str,
    crop_left: float | None,
    crop_top: float | None,
    crop_size: float | None,
) -> dict:
    base = public_base_url(context)
    crop = crop_tuple(crop_left, crop_top, crop_size)
    width, height = image_dimensions(rel)
    return {
        "original": detail_image(rel, base, None),
        "cropped": detail_image(rel, base, crop),
        "width": width,
        "height": height,
        "crop_left": crop_left,
        "crop_top": crop_top,
        "crop_size": crop_size,
    }


def category_image_payload(context: dict, obj: Category | CategoryLanding) -> dict | None:
    name = obj.image.name if obj.image else ""
    if not name and isinstance(obj, CategoryLanding):
        name = obj.source.image.name if obj.source.image else ""
    if not name:
        return None
    base = public_base_url(context)
    return {"preview": list_primary_image(name, base, None)}


def run_model_clean(instance, exclude: list[str]) -> None:
    try:
        instance.full_clean(exclude=exclude)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.message_dict) from exc


def require_filled(attrs: dict, field: str, message: str) -> None:
    if not any((attrs.get(f"{field}_{code}") or "").strip() for code in LANGUAGES):
        raise serializers.ValidationError(message)


class SiteCategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "slug",
            "name_en",
            "name_ka",
            "name_ru",
            "page_slug_en",
            "page_slug_ka",
            "page_slug_ru",
            "page_heading_en",
            "page_heading_ka",
            "page_heading_ru",
            "page_description_en",
            "page_description_ka",
            "page_description_ru",
            "seo_title_en",
            "seo_title_ka",
            "seo_title_ru",
            "seo_description_en",
            "seo_description_ka",
            "seo_description_ru",
            "image",
            "position",
            "is_active",
            "delivery_schedule_tier",
            "updated_at",
        ]

    def get_image(self, obj: Category):
        return category_image_payload(self.context, obj)

    def validate(self, attrs):
        require_filled(attrs, "name", "Name is required in at least one language.")
        return attrs

    def create(self, validated_data):
        instance = Category(**validated_data)
        run_model_clean(instance, ["name"])
        instance.save()
        schedule_translation([instance])
        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        run_model_clean(instance, ["name"])
        instance.save()
        schedule_translation([instance])
        return instance


class SiteCategoryLandingSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = CategoryLanding
        fields = [
            "id",
            "slug",
            "source",
            "source_name",
            "page_slug_en",
            "page_slug_ka",
            "page_slug_ru",
            "page_heading_en",
            "page_heading_ka",
            "page_heading_ru",
            "page_description_en",
            "page_description_ka",
            "page_description_ru",
            "seo_title_en",
            "seo_title_ka",
            "seo_title_ru",
            "seo_description_en",
            "seo_description_ka",
            "seo_description_ru",
            "image",
            "is_active",
            "updated_at",
        ]

    def get_image(self, obj: CategoryLanding):
        return category_image_payload(self.context, obj)

    def validate(self, attrs):
        require_filled(attrs, "page_slug", "Page slug is required in at least one language.")
        return attrs

    def create(self, validated_data):
        instance = CategoryLanding(**validated_data)
        run_model_clean(instance, [])
        instance.save()
        schedule_translation([instance])
        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        run_model_clean(instance, [])
        instance.save()
        schedule_translation([instance])
        return instance


class SiteOptionInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    name_en = serializers.CharField(max_length=120, allow_blank=True)
    name_ka = serializers.CharField(max_length=120, allow_blank=True)
    name_ru = serializers.CharField(max_length=120, allow_blank=True)
    price_delta = serializers.DecimalField(max_digits=10, decimal_places=2)
    weight_kg = serializers.DecimalField(
        max_digits=6, decimal_places=3, required=False, allow_null=True
    )
    position = serializers.IntegerField(min_value=0)
    is_active = serializers.BooleanField()
    crop_left = serializers.FloatField(required=False, allow_null=True)
    crop_top = serializers.FloatField(required=False, allow_null=True)
    crop_size = serializers.FloatField(required=False, allow_null=True)


class SiteOptionGroupSerializer(serializers.ModelSerializer):
    options = SiteOptionInputSerializer(many=True, write_only=True)

    class Meta:
        model = OptionGroup
        fields = [
            "id",
            "slug",
            "name_en",
            "name_ka",
            "name_ru",
            "selection_type",
            "is_required_default",
            "min_selections",
            "max_selections",
            "options",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        rows = []
        for option in instance.options.all():
            row = {
                "id": option.pk,
                "name_en": option.name_en,
                "name_ka": option.name_ka,
                "name_ru": option.name_ru,
                "price_delta": str(option.price_delta),
                "weight_kg": str(option.weight_kg) if option.weight_kg is not None else None,
                "position": option.position,
                "is_active": option.is_active,
                "crop_left": option.crop_left,
                "crop_top": option.crop_top,
                "crop_size": option.crop_size,
                "image": None,
            }
            if option.image.name:
                row["image"] = cropped_image_payload(
                    self.context,
                    option.image.name,
                    option.crop_left,
                    option.crop_top,
                    option.crop_size,
                )
            rows.append(row)
        data["options"] = rows
        return data

    def validate(self, attrs):
        max_selections = attrs.get("max_selections")
        min_selections = attrs["min_selections"]
        if max_selections is not None and max_selections < min_selections:
            raise serializers.ValidationError("Maximum must not be less than minimum.")
        options = attrs["options"]
        existing_ids = set()
        if self.instance is not None:
            existing_ids = set(self.instance.options.values_list("id", flat=True))
        for row in options:
            if row.get("id") is not None and row["id"] not in existing_ids:
                raise serializers.ValidationError("Unknown option id.")
            require_filled(row, "name", "Name is required in at least one language.")
        require_filled(attrs, "name", "Name is required in at least one language.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        options = validated_data.pop("options")
        instance = OptionGroup.objects.create(**validated_data)
        self._save_options(instance, options)
        schedule_translation([instance, *instance.options.all()])
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        options = validated_data.pop("options")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._save_options(instance, options)
        schedule_translation([instance, *instance.options.all()])
        return instance

    def _save_options(self, instance: OptionGroup, options: list[dict]) -> None:
        kept = {row["id"] for row in options if row.get("id") is not None}
        instance.options.exclude(pk__in=kept).delete()
        for row in options:
            option_id = row.get("id")
            payload = {
                "name_en": row["name_en"],
                "name_ka": row["name_ka"],
                "name_ru": row["name_ru"],
                "price_delta": row["price_delta"],
                "weight_kg": row.get("weight_kg"),
                "position": row["position"],
                "is_active": row["is_active"],
                "crop_left": row.get("crop_left"),
                "crop_top": row.get("crop_top"),
                "crop_size": row.get("crop_size"),
            }
            if option_id is None:
                Option.objects.create(group=instance, **payload)
            else:
                Option.objects.filter(pk=option_id, group=instance).update(**payload)


class SiteProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = [
            "id",
            "position",
            "alt_en",
            "alt_ka",
            "alt_ru",
            "crop_left",
            "crop_top",
            "crop_size",
            "image",
        ]

    def get_image(self, obj: ProductImage):
        return cropped_image_payload(
            self.context,
            obj.image.name,
            obj.crop_left,
            obj.crop_top,
            obj.crop_size,
        )


class SiteProductOptionGroupInputSerializer(serializers.Serializer):
    option_group = serializers.IntegerField()
    position = serializers.IntegerField(min_value=0)
    is_required = serializers.BooleanField(required=False, allow_null=True)


class SiteProductListSerializer(serializers.ModelSerializer):
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    category_name = serializers.CharField(source="category.name", read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "slug",
            "name_en",
            "name_ka",
            "name_ru",
            "base_price",
            "category",
            "category_name",
            "position",
            "is_active",
            "primary_image",
        ]

    def get_primary_image(self, obj: Product):
        first = obj.images.order_by("position", "id").first()
        if first is None:
            return None
        base = public_base_url(self.context)
        crop = crop_tuple(first.crop_left, first.crop_top, first.crop_size)
        return list_primary_image(first.image.name, base, crop)


class SiteProductSerializer(serializers.ModelSerializer):
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    option_groups = SiteProductOptionGroupInputSerializer(many=True, write_only=True, required=False)
    images = SiteProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    tech_card_name = serializers.CharField(source="tech_card.name", read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "slug",
            "name_en",
            "name_ka",
            "name_ru",
            "description_en",
            "description_ka",
            "description_ru",
            "base_price",
            "category",
            "category_name",
            "delivery_schedule_tier",
            "tech_card",
            "tech_card_name",
            "position",
            "is_active",
            "created_at",
            "option_groups",
            "images",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        links = instance.product_option_groups.select_related("option_group").order_by(
            "position", "id"
        )
        data["option_groups"] = [
            {
                "option_group": link.option_group_id,
                "option_group_name": link.option_group.name,
                "position": link.position,
                "is_required": link.is_required,
            }
            for link in links
        ]
        return data

    def validate(self, attrs):
        require_filled(attrs, "name", "Name is required in at least one language.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        option_groups = validated_data.pop("option_groups", [])
        instance = Product.objects.create(**validated_data)
        self._save_option_groups(instance, option_groups)
        schedule_translation([instance, *instance.images.all()])
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        option_groups = validated_data.pop("option_groups", [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._save_option_groups(instance, option_groups)
        schedule_translation([instance, *instance.images.all()])
        return instance

    def _save_option_groups(self, product: Product, rows: list[dict]) -> None:
        product.product_option_groups.all().delete()
        for row in rows:
            ProductOptionGroup.objects.create(
                product=product,
                option_group_id=row["option_group"],
                position=row["position"],
                is_required=row.get("is_required"),
            )


class SiteProductImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()
    alt_en = serializers.CharField(max_length=200, required=False, allow_blank=True)
    alt_ka = serializers.CharField(max_length=200, required=False, allow_blank=True)
    alt_ru = serializers.CharField(max_length=200, required=False, allow_blank=True)
    crop_left = serializers.FloatField(required=False, allow_null=True)
    crop_top = serializers.FloatField(required=False, allow_null=True)
    crop_size = serializers.FloatField(required=False, allow_null=True)


class SiteProductImagePatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = [
            "position",
            "alt_en",
            "alt_ka",
            "alt_ru",
            "crop_left",
            "crop_top",
            "crop_size",
        ]


class SiteImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()


class SiteProductImageReorderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class SiteTranslationItemSerializer(serializers.Serializer):
    key = serializers.CharField()
    kind = serializers.ChoiceField(choices=list(KIND_FIELDS))
    id = serializers.IntegerField(allow_null=True)
    fields = serializers.DictField(
        child=serializers.CharField(allow_blank=True, trim_whitespace=False)
    )

    def validate(self, attrs):
        unknown = set(attrs["fields"]) - set(KIND_FIELDS[attrs["kind"]])
        if unknown:
            raise serializers.ValidationError(f"Unknown fields: {', '.join(sorted(unknown))}.")
        if not any(value.strip() for value in attrs["fields"].values()):
            raise serializers.ValidationError("Nothing to translate.")
        return attrs


class SiteTranslationRequestSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=LANGUAGES)
    items = SiteTranslationItemSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        keys = [item["key"] for item in attrs["items"]]
        if len(keys) != len(set(keys)):
            raise serializers.ValidationError("Translation item keys must be unique.")
        return attrs


class SiteTechCardChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechCard
        fields = ["id", "name"]
