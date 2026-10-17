from decimal import Decimal

from rest_framework import serializers

from crm.models import FinancialTransaction
from inventory.models import (
    InventoryCount,
    InventoryCountLine,
    Production,
    StockMovement,
    Supplier,
    Supply,
    SupplyLine,
    SupplyReceipt,
    WriteOff,
    WriteOffLine,
    WriteOffReason,
)
from menu.models import Ingredient, SemiProduct
from menu.serializers import ComponentLineSerializer, component_payload


def show_costs(context: dict) -> bool:
    return context["show_costs"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "phone", "comment"]


class WriteOffReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = WriteOffReason
        fields = ["id", "name"]


class SupplyLineInputSerializer(serializers.Serializer):
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    total = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))


def public_media_url(url: str) -> str:
    if url.startswith("/"):
        return url
    return f"/{url}"


class SupplyReceiptSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = SupplyReceipt
        fields = ["id", "image", "recognized"]

    def get_image(self, instance: SupplyReceipt) -> str:
        return public_media_url(instance.image.url)


def transaction_payload(transaction: FinancialTransaction | None) -> dict | None:
    if transaction is None:
        return None
    return {
        "id": transaction.pk,
        "date": transaction.date.isoformat(),
        "amount": str(transaction.amount),
        "counterparty_name": transaction.counterparty_name,
        "description": transaction.description,
        "account_name": transaction.account.name,
    }


class SupplySerializer(serializers.ModelSerializer):
    lines = SupplyLineInputSerializer(many=True, write_only=True)
    receipts = serializers.PrimaryKeyRelatedField(queryset=SupplyReceipt.objects.all(), many=True)
    financial_transaction = serializers.PrimaryKeyRelatedField(
        queryset=FinancialTransaction.objects.select_related("account"),
        allow_null=True,
    )

    class Meta:
        model = Supply
        fields = ["id", "date", "supplier", "financial_transaction", "comment", "lines", "receipts", "created_at"]
        read_only_fields = ["created_at"]
        extra_kwargs = {
            "supplier": {"required": True},
            "comment": {"required": True},
            "receipts": {"required": True},
        }

    def validate_financial_transaction(self, value: FinancialTransaction | None) -> FinancialTransaction | None:
        if value is None:
            return value
        if value.kind != FinancialTransaction.KIND_EXPENSE or value.expense_type != FinancialTransaction.EXPENSE_PRODUCTS:
            raise serializers.ValidationError("Only product expenses can be linked to a supply.")
        linked = Supply.objects.filter(financial_transaction=value)
        if self.instance is not None:
            linked = linked.exclude(pk=self.instance.pk)
        if linked.exists():
            raise serializers.ValidationError("This bank transaction is already linked to another supply.")
        return value

    def validate_lines(self, value: list[dict]) -> list[dict]:
        if not value:
            raise serializers.ValidationError("Add at least one line.")
        return value

    def validate_receipts(self, value: list[SupplyReceipt]) -> list[SupplyReceipt]:
        for receipt in value:
            if receipt.supply_id is not None and (self.instance is None or receipt.supply_id != self.instance.pk):
                raise serializers.ValidationError("This receipt is already linked to another supply.")
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["supplier_name"] = instance.supplier.name if instance.supplier_id is not None else None
        data["financial_transaction"] = transaction_payload(instance.financial_transaction)
        lines = []
        total = Decimal("0")
        for line in instance.lines.select_related("ingredient"):
            total += line.total
            lines.append(
                {
                    "id": line.pk,
                    "ingredient": line.ingredient_id,
                    "name": line.ingredient.name,
                    "unit": line.ingredient.unit,
                    "quantity": str(line.quantity),
                    "total": str(line.total),
                }
            )
        data["lines"] = lines
        data["receipts"] = [
            {"id": receipt.pk, "image": public_media_url(receipt.image.url)} for receipt in instance.receipts.all()
        ]
        data["total"] = str(total)
        return data

    def create(self, validated_data):
        lines = validated_data.pop("lines")
        receipts = validated_data.pop("receipts")
        validated_data["created_by"] = self.context["request"].user
        instance = Supply.objects.create(**validated_data)
        self._save_lines(instance, lines)
        self._save_receipts(instance, receipts)
        return instance

    def update(self, instance, validated_data):
        lines = validated_data.pop("lines")
        receipts = validated_data.pop("receipts")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._save_lines(instance, lines)
        self._save_receipts(instance, receipts)
        return instance

    def _save_lines(self, instance: Supply, lines: list[dict]) -> None:
        instance.lines.all().delete()
        for line in lines:
            SupplyLine.objects.create(supply=instance, **line)

    def _save_receipts(self, instance: Supply, receipts: list[SupplyReceipt]) -> None:
        instance.receipts.exclude(pk__in=[receipt.pk for receipt in receipts]).delete()
        for receipt in receipts:
            receipt.supply = instance
            receipt.save(update_fields=["supply"])
        instance._prefetched_objects_cache = {}


class ProductionSerializer(serializers.ModelSerializer):
    semi_product = serializers.PrimaryKeyRelatedField(queryset=SemiProduct.objects.filter(is_produced=True))
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))

    class Meta:
        model = Production
        fields = ["id", "date", "semi_product", "quantity", "comment", "created_at"]
        read_only_fields = ["created_at"]
        extra_kwargs = {"comment": {"required": True}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["semi_product_name"] = instance.semi_product.name
        data["unit"] = instance.semi_product.unit
        data["created_by_name"] = user_name(instance.created_by)
        data["consumed"] = movement_payloads(
            instance.movements.filter(kind=StockMovement.KIND_PRODUCTION_OUT),
            self.context,
        )
        if show_costs(self.context):
            output = instance.movements.filter(kind=StockMovement.KIND_PRODUCTION_IN).first()
            data["unit_cost"] = str(output.unit_cost) if output is not None else None
        return data

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return Production.objects.create(**validated_data)


def user_name(user) -> str | None:
    if user is None:
        return None
    return user.get_full_name() or user.username


class WriteOffSerializer(serializers.ModelSerializer):
    lines = ComponentLineSerializer(many=True, write_only=True)

    class Meta:
        model = WriteOff
        fields = ["id", "date", "reason", "comment", "lines", "created_at"]
        read_only_fields = ["created_at"]
        extra_kwargs = {"comment": {"required": True}}

    def validate_lines(self, value: list[dict]) -> list[dict]:
        if not value:
            raise serializers.ValidationError("Add at least one line.")
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["reason_name"] = instance.reason.name
        data["created_by_name"] = user_name(instance.created_by)
        data["lines"] = [
            component_payload(line)
            for line in instance.lines.select_related("ingredient", "semi_product")
        ]
        if show_costs(self.context):
            total = Decimal("0")
            for movement in StockMovement.objects.filter(write_off_line__write_off=instance):
                total -= movement.quantity * movement.unit_cost
            data["total_cost"] = str(total.quantize(Decimal("0.01")))
        return data

    def create(self, validated_data):
        lines = validated_data.pop("lines")
        validated_data["created_by"] = self.context["request"].user
        instance = WriteOff.objects.create(**validated_data)
        self._save_lines(instance, lines)
        return instance

    def update(self, instance, validated_data):
        lines = validated_data.pop("lines")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._save_lines(instance, lines)
        return instance

    def _save_lines(self, instance: WriteOff, lines: list[dict]) -> None:
        instance.lines.all().delete()
        for line in lines:
            WriteOffLine.objects.create(write_off=instance, **line)


class InventoryCountLineInputSerializer(serializers.Serializer):
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all(), allow_null=True)
    semi_product = serializers.PrimaryKeyRelatedField(
        queryset=SemiProduct.objects.filter(is_produced=True),
        allow_null=True,
    )
    actual_quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0"))
    unit_cost = serializers.DecimalField(
        max_digits=14,
        decimal_places=6,
        min_value=Decimal("0"),
        allow_null=True,
    )

    def validate(self, attrs):
        if (attrs["ingredient"] is None) == (attrs["semi_product"] is None):
            raise serializers.ValidationError("Pass either ingredient or semi_product.")
        return attrs


class InventoryCountSerializer(serializers.ModelSerializer):
    lines = InventoryCountLineInputSerializer(many=True, write_only=True)

    class Meta:
        model = InventoryCount
        fields = ["id", "date", "status", "comment", "lines", "created_at", "closed_at"]
        read_only_fields = ["status", "created_at", "closed_at"]
        extra_kwargs = {"comment": {"required": True}}

    def validate(self, attrs):
        if self.instance is not None and self.instance.status == InventoryCount.STATUS_CLOSED:
            raise serializers.ValidationError("A closed inventory count cannot be edited.")
        keys = [
            ("ingredient", line["ingredient"].pk) if line["ingredient"] is not None else ("semi", line["semi_product"].pk)
            for line in attrs["lines"]
        ]
        if len(keys) != len(set(keys)):
            raise serializers.ValidationError("Each item can be counted only once.")
        if not show_costs(self.context) and any(line["unit_cost"] is not None for line in attrs["lines"]):
            raise serializers.ValidationError("Only finance admins can set unit costs.")
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_name"] = user_name(instance.created_by)
        lines = []
        for line in instance.lines.select_related("ingredient", "semi_product"):
            payload = component_payload(line)
            payload.pop("quantity")
            payload["actual_quantity"] = str(line.actual_quantity)
            payload["expected_quantity"] = (
                str(line.expected_quantity) if line.expected_quantity is not None else None
            )
            if show_costs(self.context):
                payload["unit_cost"] = str(line.unit_cost) if line.unit_cost is not None else None
            lines.append(payload)
        data["lines"] = lines
        return data

    def create(self, validated_data):
        lines = validated_data.pop("lines")
        validated_data["created_by"] = self.context["request"].user
        instance = InventoryCount.objects.create(**validated_data)
        self._save_lines(instance, lines)
        return instance

    def update(self, instance, validated_data):
        lines = validated_data.pop("lines")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._save_lines(instance, lines)
        return instance

    def _save_lines(self, instance: InventoryCount, lines: list[dict]) -> None:
        instance.lines.all().delete()
        for line in lines:
            InventoryCountLine.objects.create(count=instance, **line)


def movement_document(movement: StockMovement) -> dict:
    if movement.supply_line_id is not None:
        return {"type": "supply", "id": movement.supply_line.supply_id}
    if movement.production_id is not None:
        return {"type": "production", "id": movement.production_id}
    if movement.crm_order_id is not None:
        return {"type": "crm_order", "id": movement.crm_order_id}
    if movement.write_off_line_id is not None:
        return {"type": "write_off", "id": movement.write_off_line.write_off_id}
    return {"type": "inventory_count", "id": movement.inventory_count_line.count_id}


def movement_payloads(movements, context: dict) -> list[dict]:
    rows = []
    for movement in movements.select_related(
        "ingredient",
        "semi_product",
        "supply_line",
        "write_off_line",
        "inventory_count_line",
    ):
        component = movement.component
        row = {
            "id": movement.pk,
            "date": movement.date.isoformat(),
            "kind": movement.kind,
            "ingredient": movement.ingredient_id,
            "semi_product": movement.semi_product_id,
            "name": component.name,
            "unit": component.unit,
            "quantity": str(movement.quantity),
            "document": movement_document(movement),
        }
        if show_costs(context):
            row["unit_cost"] = str(movement.unit_cost)
        rows.append(row)
    return rows


class StockQuerySerializer(serializers.Serializer):
    date = serializers.DateField(required=False)


class MovementQuerySerializer(serializers.Serializer):
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all(), required=False)
    semi_product = serializers.PrimaryKeyRelatedField(queryset=SemiProduct.objects.all(), required=False)

    def validate(self, attrs):
        if ("ingredient" in attrs) == ("semi_product" in attrs):
            raise serializers.ValidationError("Pass either ingredient or semi_product.")
        return attrs


class FinancialTransactionQuerySerializer(serializers.Serializer):
    supply = serializers.IntegerField(required=False)
