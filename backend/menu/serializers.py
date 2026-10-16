from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from catalog.models import Option
from catalog.responsive_urls import detail_image
from menu.models import (
    Ingredient,
    IngredientCategory,
    Modifier,
    ModifierGroup,
    SemiProduct,
    SemiProductLine,
    TechCard,
    TechCardCategory,
    TechCardLine,
    TechCardModifierGroup,
    TechCardModifierLine,
    TechCardSection,
)
from menu.recipes import missing_modifier_compositions, tech_card_cost

QUANTITY_FIELD = {"max_digits": 12, "decimal_places": 3, "min_value": Decimal("0.001")}
LOSS_FIELD = {
    "max_digits": 5,
    "decimal_places": 2,
    "min_value": Decimal("0"),
    "max_value": Decimal("99.99"),
}


def show_costs(context: dict) -> bool:
    return context["show_costs"]


def drop_costs(data: dict, context: dict, fields: list[str]) -> dict:
    if not show_costs(context):
        for field in fields:
            data.pop(field)
    return data


class IngredientCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IngredientCategory
        fields = ["id", "name", "position"]


class IngredientSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)

    class Meta:
        model = Ingredient
        fields = ["id", "name", "category", "category_name", "unit", "avg_cost", "is_active"]
        read_only_fields = ["avg_cost"]

    def to_representation(self, instance):
        return drop_costs(super().to_representation(instance), self.context, ["avg_cost"])


class ComponentLineSerializer(serializers.Serializer):
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all(), allow_null=True)
    semi_product = serializers.PrimaryKeyRelatedField(queryset=SemiProduct.objects.all(), allow_null=True)
    quantity = serializers.DecimalField(**QUANTITY_FIELD)

    def validate(self, attrs):
        if (attrs["ingredient"] is None) == (attrs["semi_product"] is None):
            raise serializers.ValidationError("Pass either ingredient or semi_product.")
        return attrs


class RecipeLineSerializer(ComponentLineSerializer):
    loss_percent = serializers.DecimalField(**LOSS_FIELD)


def component_payload(line) -> dict:
    component = line.component
    return {
        "id": line.pk,
        "ingredient": line.ingredient_id,
        "semi_product": line.semi_product_id,
        "name": component.name,
        "unit": component.unit,
        "quantity": str(line.quantity),
    }


def recipe_line_payload(line) -> dict:
    payload = component_payload(line)
    payload["loss_percent"] = str(line.loss_percent)
    return payload


def menu_image_rows(rows, request) -> list[dict]:
    public_base_url = request.build_absolute_uri("/").rstrip("/")
    return [
        {
            "id": row.pk,
            "image": detail_image(row.image.name, public_base_url),
            "position": row.position,
        }
        for row in rows
    ]


class MenuImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()


class SemiProductSerializer(serializers.ModelSerializer):
    lines = RecipeLineSerializer(many=True, write_only=True)

    class Meta:
        model = SemiProduct
        fields = [
            "id",
            "name",
            "unit",
            "yield_quantity",
            "is_produced",
            "avg_cost",
            "is_active",
            "method",
            "lines",
        ]
        read_only_fields = ["avg_cost"]
        extra_kwargs = {"method": {"required": True, "allow_blank": True}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["lines"] = [
            recipe_line_payload(line)
            for line in instance.lines.select_related("ingredient", "semi_product")
        ]
        data["images"] = menu_image_rows(instance.images.all(), self.context["request"])
        return drop_costs(data, self.context, ["avg_cost"])

    @transaction.atomic
    def create(self, validated_data):
        lines = validated_data.pop("lines")
        instance = SemiProduct.objects.create(**validated_data)
        self._save_lines(instance, lines)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        lines = validated_data.pop("lines")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._save_lines(instance, lines)
        return instance

    def _save_lines(self, instance: SemiProduct, lines: list[dict]) -> None:
        instance.lines.all().delete()
        for position, line in enumerate(lines):
            SemiProductLine.objects.create(parent=instance, position=position, **line)
        if any(line["semi_product"] is not None for line in lines):
            ensure_cycle_free(instance)


def ensure_cycle_free(instance: SemiProduct) -> None:
    errors = cycle_errors(instance)
    if errors:
        raise serializers.ValidationError({"lines": errors})


def _nested_semi_products(pk: int) -> list[int]:
    return list(
        SemiProductLine.objects.filter(parent_id=pk, semi_product__isnull=False).values_list(
            "semi_product_id", flat=True
        )
    )


def cycle_errors(instance: SemiProduct) -> list[str]:
    visited: set[int] = set()
    stack = _nested_semi_products(instance.pk)
    while stack:
        pk = stack.pop()
        if pk == instance.pk:
            return [f"Semi-product {instance.name} contains itself."]
        if pk in visited:
            continue
        visited.add(pk)
        stack.extend(_nested_semi_products(pk))
    return []


class ModifierInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField(max_length=120)
    catalog_option = serializers.PrimaryKeyRelatedField(queryset=Option.objects.all(), allow_null=True)
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all(), allow_null=True)
    semi_product = serializers.PrimaryKeyRelatedField(queryset=SemiProduct.objects.all(), allow_null=True)
    is_active = serializers.BooleanField()

    def validate(self, attrs):
        if attrs["ingredient"] is not None and attrs["semi_product"] is not None:
            raise serializers.ValidationError("Pass ingredient or semi_product, not both.")
        return attrs


class ModifierGroupSerializer(serializers.ModelSerializer):
    modifiers = ModifierInputSerializer(many=True, write_only=True)

    class Meta:
        model = ModifierGroup
        fields = [
            "id",
            "name",
            "selection_type",
            "is_required",
            "min_selections",
            "max_selections",
            "position",
            "modifiers",
        ]
        extra_kwargs = {
            "is_required": {"required": True},
            "min_selections": {"required": True},
            "max_selections": {"required": True},
            "position": {"required": True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["modifiers"] = [
            {
                "id": modifier.pk,
                "name": modifier.name,
                "catalog_option": modifier.catalog_option_id,
                "catalog_option_label": option_label(modifier.catalog_option),
                "ingredient": modifier.ingredient_id,
                "semi_product": modifier.semi_product_id,
                "is_active": modifier.is_active,
            }
            for modifier in instance.modifiers.select_related("catalog_option__group")
        ]
        return data

    def validate(self, attrs):
        max_selections = attrs["max_selections"]
        if max_selections is not None and max_selections < attrs["min_selections"]:
            raise serializers.ValidationError("Maximum must not be less than minimum.")
        names = [row["name"] for row in attrs["modifiers"]]
        if len(names) != len(set(names)):
            raise serializers.ValidationError("Modifier names must be unique within a group.")
        options = [row["catalog_option"].pk for row in attrs["modifiers"] if row["catalog_option"] is not None]
        if len(options) != len(set(options)):
            raise serializers.ValidationError("A website option can be linked to one modifier only.")
        existing_ids = set()
        if self.instance is not None:
            existing_ids = set(self.instance.modifiers.values_list("id", flat=True))
        for row in attrs["modifiers"]:
            if row["id"] is not None and row["id"] not in existing_ids:
                raise serializers.ValidationError("Unknown modifier id.")
        taken = Modifier.objects.filter(catalog_option_id__in=options)
        if self.instance is not None:
            taken = taken.exclude(group=self.instance)
        if taken.exists():
            raise serializers.ValidationError("A website option can be linked to one modifier only.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        modifiers = validated_data.pop("modifiers")
        instance = ModifierGroup.objects.create(**validated_data)
        self._save_modifiers(instance, modifiers)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        modifiers = validated_data.pop("modifiers")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._save_modifiers(instance, modifiers)
        return instance

    def _save_modifiers(self, instance: ModifierGroup, modifiers: list[dict]) -> None:
        kept = {row["id"] for row in modifiers if row["id"] is not None}
        removed = instance.modifiers.exclude(pk__in=kept)
        if (
            TechCardModifierLine.objects.filter(modifier__in=removed).exists()
            or removed.filter(crm_order_items__isnull=False).exists()
        ):
            raise serializers.ValidationError("Modifier is used in tech cards or orders, deactivate it instead.")
        removed.delete()
        instance.modifiers.update(catalog_option=None)
        for position, row in enumerate(modifiers):
            fields = {
                "name": row["name"],
                "catalog_option": row["catalog_option"],
                "ingredient": row["ingredient"],
                "semi_product": row["semi_product"],
                "is_active": row["is_active"],
                "position": position,
            }
            if row["id"] is None:
                Modifier.objects.create(group=instance, **fields)
            else:
                Modifier.objects.filter(pk=row["id"]).update(**fields)


def option_label(option: Option | None) -> str | None:
    if option is None:
        return None
    return f"{option.group.name}: {option.name}"


class CatalogOptionSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    modifier = serializers.SerializerMethodField()

    class Meta:
        model = Option
        fields = ["id", "label", "weight_kg", "modifier"]

    def get_label(self, obj: Option) -> str:
        return option_label(obj)

    def get_modifier(self, obj: Option) -> int | None:
        return self.context["modifier_by_option"].get(obj.pk)


class TechCardSectionInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    method = serializers.CharField(allow_blank=True, trim_whitespace=False)
    lines = RecipeLineSerializer(many=True)

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Section name is required.")
        return name


class TechCardGroupInputSerializer(serializers.Serializer):
    group = serializers.PrimaryKeyRelatedField(queryset=ModifierGroup.objects.all())
    is_required = serializers.BooleanField(allow_null=True)


class TechCardModifierLineInputSerializer(RecipeLineSerializer):
    modifier = serializers.PrimaryKeyRelatedField(queryset=Modifier.objects.all())
    scales_by_weight = serializers.BooleanField()


class TechCardCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TechCardCategory
        fields = ["id", "name", "position"]


class TechCardSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)
    lines = RecipeLineSerializer(many=True, write_only=True)
    sections = TechCardSectionInputSerializer(many=True, write_only=True)
    modifier_groups = TechCardGroupInputSerializer(many=True, write_only=True)
    modifier_lines = TechCardModifierLineInputSerializer(many=True, write_only=True)

    class Meta:
        model = TechCard
        fields = [
            "id",
            "name",
            "category",
            "category_name",
            "kind",
            "basis_weight_kg",
            "basis_quantity",
            "method",
            "is_active",
            "lines",
            "sections",
            "modifier_groups",
            "modifier_lines",
        ]
        extra_kwargs = {
            "basis_weight_kg": {"required": True, "allow_null": True},
            "basis_quantity": {"required": True, "allow_null": True},
            "method": {"required": True, "allow_blank": True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["lines"] = [
            recipe_line_payload(line)
            for line in instance.lines.filter(section__isnull=True).select_related("ingredient", "semi_product")
        ]
        data["sections"] = [
            {
                "id": section.pk,
                "name": section.name,
                "method": section.method,
                "position": section.position,
                "lines": [
                    recipe_line_payload(line)
                    for line in section.lines.select_related("ingredient", "semi_product")
                ],
            }
            for section in instance.sections.all()
        ]
        data["modifier_groups"] = [
            {
                "id": link.pk,
                "group": link.group_id,
                "group_name": link.group.name,
                "selection_type": link.group.selection_type,
                "is_required": link.is_required,
                "effective_is_required": link.effective_is_required,
                "min_selections": link.group.min_selections,
                "max_selections": link.group.max_selections,
                "modifiers": [
                    {"id": modifier.pk, "name": modifier.name}
                    for modifier in link.group.modifiers.filter(is_active=True)
                ],
            }
            for link in instance.modifier_groups.select_related("group")
        ]
        modifier_lines = []
        for line in instance.modifier_lines.select_related("ingredient", "semi_product", "modifier"):
            payload = recipe_line_payload(line)
            payload["modifier"] = line.modifier_id
            payload["scales_by_weight"] = line.scales_by_weight
            modifier_lines.append(payload)
        data["modifier_lines"] = modifier_lines
        data["missing_modifiers"] = [modifier.pk for modifier in missing_modifier_compositions(instance)]
        data["products"] = [
            {"id": product.pk, "name": product.name}
            for product in instance.products.order_by("name")
        ]
        data["images"] = menu_image_rows(instance.images.all(), self.context["request"])
        if show_costs(self.context):
            weight = instance.basis_weight_kg if instance.kind == TechCard.KIND_WEIGHTED else None
            data["base_cost"] = str(tech_card_cost(instance, [], weight))
        return data

    def validate(self, attrs):
        kind = attrs["kind"]
        basis = attrs["basis_weight_kg"]
        pieces = attrs["basis_quantity"]
        if kind == TechCard.KIND_WEIGHTED and basis is None:
            raise serializers.ValidationError(
                {"basis_weight_kg": "Basis weight is required for a weighted tech card."}
            )
        if kind == TechCard.KIND_WEIGHTED and pieces is not None:
            raise serializers.ValidationError(
                {"basis_quantity": "A weighted tech card has no basis quantity."}
            )
        if kind == TechCard.KIND_PIECE and pieces is None:
            raise serializers.ValidationError(
                {"basis_quantity": "Basis quantity is required for a piece tech card."}
            )
        if kind == TechCard.KIND_PIECE and basis is not None:
            raise serializers.ValidationError({"basis_weight_kg": "A piece tech card has no basis weight."})
        section_names = [row["name"] for row in attrs["sections"]]
        if len(section_names) != len(set(section_names)):
            raise serializers.ValidationError("A section name is used twice.")
        group_ids = [row["group"].pk for row in attrs["modifier_groups"]]
        if len(group_ids) != len(set(group_ids)):
            raise serializers.ValidationError("A modifier group is linked twice.")
        for row in attrs["modifier_lines"]:
            if row["modifier"].group_id not in group_ids:
                raise serializers.ValidationError(
                    f"Modifier {row['modifier'].name} is not in the linked groups."
                )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        children = self._pop_children(validated_data)
        instance = TechCard.objects.create(**validated_data)
        self._save_children(instance, children)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        children = self._pop_children(validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._save_children(instance, children)
        return instance

    def _pop_children(self, validated_data: dict) -> dict:
        return {
            "lines": validated_data.pop("lines"),
            "sections": validated_data.pop("sections"),
            "modifier_groups": validated_data.pop("modifier_groups"),
            "modifier_lines": validated_data.pop("modifier_lines"),
        }

    def _save_children(self, instance: TechCard, children: dict) -> None:
        instance.lines.all().delete()
        instance.sections.all().delete()
        instance.modifier_groups.all().delete()
        instance.modifier_lines.all().delete()
        for position, section in enumerate(children["sections"]):
            saved = TechCardSection.objects.create(
                tech_card=instance,
                name=section["name"],
                method=section["method"],
                position=position,
            )
            for line_position, line in enumerate(section["lines"]):
                TechCardLine.objects.create(
                    tech_card=instance,
                    section=saved,
                    position=line_position,
                    **line,
                )
        for position, line in enumerate(children["lines"]):
            TechCardLine.objects.create(tech_card=instance, position=position, **line)
        for position, row in enumerate(children["modifier_groups"]):
            TechCardModifierGroup.objects.create(
                tech_card=instance,
                group=row["group"],
                is_required=row["is_required"],
                position=position,
            )
        for position, line in enumerate(children["modifier_lines"]):
            TechCardModifierLine.objects.create(tech_card=instance, position=position, **line)


class TechCardCostQuerySerializer(serializers.Serializer):
    weight_kg = serializers.DecimalField(max_digits=6, decimal_places=3, required=False, allow_null=True)
    modifiers = serializers.RegexField(regex=r"^(\d+:\d+)(,\d+:\d+)*$", required=False, allow_blank=True)

    def modifier_pairs(self) -> list[tuple[Modifier, int]]:
        raw = self.validated_data.get("modifiers", "")
        if not raw:
            return []
        pairs = [chunk.split(":") for chunk in raw.split(",")]
        by_id = Modifier.objects.in_bulk([int(pk) for pk, _qty in pairs])
        if len(by_id) != len({int(pk) for pk, _qty in pairs}):
            raise serializers.ValidationError({"modifiers": "Unknown modifier id."})
        return [(by_id[int(pk)], int(quantity)) for pk, quantity in pairs]


class MissingModifierLineSerializer(serializers.Serializer):
    tech_card = serializers.IntegerField()
    tech_card_name = serializers.CharField()
    modifier = serializers.IntegerField()
    modifier_name = serializers.CharField()
    group_name = serializers.CharField()
