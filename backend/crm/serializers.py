from decimal import Decimal

from rest_framework import serializers

from accounts.models import chef_identity
from catalog.responsive_urls import detail_image
from crm.flowwow import sync_flowwow_order_status_from_crm
from crm.flowwow_statement import ACCOUNT_NAME as FLOWWOW_ACCOUNT_NAME
from crm.google_maps import cached_google_maps_url
from crm.history import USER_ID_FIELDS, record_crm_order_event, snapshot_crm_order
from crm.manual_transactions import PAIR_CREATE, PAIR_LINK, PAIR_NONE
from crm.models import (
    CrmOrder,
    CrmOrderEvent,
    CrmOrderImage,
    CrmOrderItem,
    CrmOrderItemLine,
    CrmOrderItemModifier,
    FinancialAccount,
    FinancialTransaction,
    ResolvedTelegramPhone,
)
from crm.phone import links_for_stored
from menu.models import Ingredient, Modifier, SemiProduct, TechCard
from menu.recipes import order_cost, order_item_errors
from orders.email import schedule_order_confirmed_email


def _telegram_resolved(context: dict) -> dict[str, bool]:
    flags = context.get("telegram_resolved")
    if flags is None:
        flags = dict(ResolvedTelegramPhone.objects.values_list("number", "resolved"))
        context["telegram_resolved"] = flags
    return flags


def order_phones(instance: CrmOrder, context: dict) -> list[dict[str, str | None]]:
    flags = _telegram_resolved(context)
    phones: list[dict[str, str | None]] = []
    for phone in instance.phones:
        links = links_for_stored(phone["value"])
        value = phone["value"]
        if value.isdigit() and value in flags and not flags[value]:
            links["telegram"] = None
        links["party"] = phone["party"]
        phones.append(links)
    return phones


class CrmOrderImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = CrmOrderImage
        fields = ["id", "image", "position"]

    def get_image(self, obj: CrmOrderImage) -> dict[str, str]:
        public_base_url = self.context["request"].build_absolute_uri("/").rstrip("/")
        return detail_image(obj.image.name, public_base_url)


class CrmOrderItemModifierSerializer(serializers.ModelSerializer):
    modifier_name = serializers.CharField(source="modifier.name", read_only=True)
    group = serializers.IntegerField(source="modifier.group_id", read_only=True)

    class Meta:
        model = CrmOrderItemModifier
        fields = ["id", "modifier", "modifier_name", "group", "quantity"]


class CrmOrderItemLineSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()

    class Meta:
        model = CrmOrderItemLine
        fields = ["id", "ingredient", "semi_product", "name", "unit", "quantity"]

    def get_name(self, obj: CrmOrderItemLine) -> str:
        return obj.component.name

    def get_unit(self, obj: CrmOrderItemLine) -> str:
        return obj.component.unit


class CrmOrderItemSerializer(serializers.ModelSerializer):
    tech_card_name = serializers.CharField(source="tech_card.name", read_only=True, allow_null=True)
    tech_card_kind = serializers.CharField(source="tech_card.kind", read_only=True, allow_null=True)
    modifiers = CrmOrderItemModifierSerializer(many=True, read_only=True)
    lines = CrmOrderItemLineSerializer(many=True, read_only=True)

    class Meta:
        model = CrmOrderItem
        fields = [
            "id",
            "tech_card",
            "tech_card_name",
            "tech_card_kind",
            "name",
            "quantity",
            "weight_kg",
            "price",
            "comment",
            "needs_review",
            "position",
            "modifiers",
            "lines",
        ]


class CrmOrderItemModifierInputSerializer(serializers.Serializer):
    modifier = serializers.PrimaryKeyRelatedField(queryset=Modifier.objects.select_related("group"))
    quantity = serializers.IntegerField(min_value=1)


class CrmOrderItemLineInputSerializer(serializers.Serializer):
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all(), allow_null=True)
    semi_product = serializers.PrimaryKeyRelatedField(queryset=SemiProduct.objects.all(), allow_null=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))

    def validate(self, attrs):
        if (attrs["ingredient"] is None) == (attrs["semi_product"] is None):
            raise serializers.ValidationError("Pass either ingredient or semi_product.")
        return attrs


class CrmOrderItemInputSerializer(serializers.Serializer):
    tech_card = serializers.PrimaryKeyRelatedField(queryset=TechCard.objects.all(), allow_null=True)
    name = serializers.CharField(max_length=255, allow_blank=True)
    quantity = serializers.IntegerField(min_value=1)
    weight_kg = serializers.DecimalField(max_digits=6, decimal_places=3, allow_null=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    comment = serializers.CharField(allow_blank=True)
    needs_review = serializers.BooleanField()
    modifiers = CrmOrderItemModifierInputSerializer(many=True)
    lines = CrmOrderItemLineInputSerializer(many=True)

    def validate(self, attrs):
        if attrs["tech_card"] is None and not attrs["name"].strip():
            raise serializers.ValidationError("Item without a tech card needs a name.")
        errors = order_item_errors(
            attrs["tech_card"],
            attrs["weight_kg"],
            [(row["modifier"], row["quantity"]) for row in attrs["modifiers"]],
        )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


def replace_crm_order_items(order: CrmOrder, items: list[dict]) -> None:
    order.items.all().delete()
    for position, item in enumerate(items):
        crm_item = CrmOrderItem.objects.create(
            order=order,
            tech_card=item["tech_card"],
            name=item["name"],
            quantity=item["quantity"],
            weight_kg=item["weight_kg"],
            price=item["price"],
            comment=item["comment"],
            needs_review=item["needs_review"],
            position=position,
        )
        for row in item["modifiers"]:
            CrmOrderItemModifier.objects.create(item=crm_item, modifier=row["modifier"], quantity=row["quantity"])
        for row in item["lines"]:
            CrmOrderItemLine.objects.create(
                item=crm_item,
                ingredient=row["ingredient"],
                semi_product=row["semi_product"],
                quantity=row["quantity"],
            )


class CrmOrderSerializer(serializers.ModelSerializer):
    images = CrmOrderImageSerializer(many=True, read_only=True)
    items = CrmOrderItemSerializer(many=True, read_only=True)
    cake_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    delivery_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    prepayment = serializers.DecimalField(max_digits=10, decimal_places=2)
    phones = serializers.SerializerMethodField()
    taken_by_name = serializers.CharField(read_only=True, allow_null=True)
    taken_by_telegram_url = serializers.CharField(read_only=True, allow_null=True)
    taken_by_gender = serializers.CharField(read_only=True, allow_null=True)
    created_by_name = serializers.CharField(read_only=True, allow_null=True)
    created_by_telegram_url = serializers.CharField(read_only=True, allow_null=True)
    created_by_gender = serializers.CharField(read_only=True, allow_null=True)
    delivered_by_name = serializers.CharField(read_only=True, allow_null=True)
    delivered_by_telegram_url = serializers.CharField(read_only=True, allow_null=True)
    delivered_by_gender = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = CrmOrder
        fields = [
            "id",
            "client_token",
            "date",
            "time_start",
            "time_end",
            "when_ready",
            "contact",
            "is_gift",
            "phones",
            "nickname",
            "delivery_address",
            "delivery_distance_meters",
            "delivery_duration_seconds",
            "fulfillment_type",
            "status",
            "taken_by_name",
            "taken_by_telegram_url",
            "taken_by_gender",
            "created_by_name",
            "created_by_telegram_url",
            "created_by_gender",
            "delivered_by_name",
            "delivered_by_telegram_url",
            "delivered_by_gender",
            "weight",
            "filling",
            "description",
            "internal_description",
            "cake_price",
            "delivery_price",
            "prepayment",
            "is_paid",
            "payment_type",
            "payment_date",
            "created_at",
            "updated_at",
            "images",
            "items",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get("show_food_cost"):
            data["food_cost"] = str(order_cost(instance))
        if instance.taken_by_id:
            name, url, _nick, gender = chef_identity(instance.taken_by)
            data["taken_by_name"] = name
            data["taken_by_telegram_url"] = url
            data["taken_by_gender"] = gender
        else:
            data["taken_by_name"] = None
            data["taken_by_telegram_url"] = None
            data["taken_by_gender"] = None
        if instance.created_by_id:
            name, url, _nick, gender = chef_identity(instance.created_by)
            data["created_by_name"] = name
            data["created_by_telegram_url"] = url
            data["created_by_gender"] = gender
        else:
            data["created_by_name"] = None
            data["created_by_telegram_url"] = None
            data["created_by_gender"] = None
        if instance.delivered_by_id:
            name, url, _nick, gender = chef_identity(instance.delivered_by)
            data["delivered_by_name"] = name
            data["delivered_by_telegram_url"] = url
            data["delivered_by_gender"] = gender
        else:
            data["delivered_by_name"] = None
            data["delivered_by_telegram_url"] = None
            data["delivered_by_gender"] = None
        return data

    def get_phones(self, instance: CrmOrder) -> list[dict[str, str | None]]:
        return order_phones(instance, self.context)


def _chef_identity_cached(user, cache: dict) -> tuple[str, str | None, str | None, str]:
    found = cache.get(user.id)
    if found is not None:
        return found
    identity = chef_identity(user)
    cache[user.id] = identity
    return identity


def _user_change_value(user_id: int | None, users_by_id: dict, cache: dict) -> dict | None:
    if user_id is None:
        return None
    user = users_by_id.get(user_id)
    if user is None:
        return {"id": user_id, "name": None, "telegram_url": None, "gender": None}
    name, url, _nick, gender = _chef_identity_cached(user, cache)
    return {"id": user.id, "name": name, "telegram_url": url, "gender": gender}


class CrmOrderEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(read_only=True, allow_null=True)
    actor_telegram_url = serializers.CharField(read_only=True, allow_null=True)
    actor_gender = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = CrmOrderEvent
        fields = [
            "id",
            "created_at",
            "action",
            "source",
            "actor_name",
            "actor_telegram_url",
            "actor_gender",
            "changes",
        ]

    def to_representation(self, instance: CrmOrderEvent):
        data = super().to_representation(instance)
        request = self.context["request"]
        users_by_id = self.context["users_by_id"]
        cache = self.context["identities"]
        changes = {key: value for key, value in instance.changes.items()}
        if not request.user.is_staff:
            changes.pop("internal_description", None)
        for field in USER_ID_FIELDS:
            change = changes.get(field)
            if change is None:
                continue
            changes[field] = {
                "old": _user_change_value(change["old"], users_by_id, cache),
                "new": _user_change_value(change["new"], users_by_id, cache),
            }
        data["changes"] = changes
        if instance.actor_id is None:
            data["actor_name"] = None
            data["actor_telegram_url"] = None
            data["actor_gender"] = None
        else:
            name, url, _nick, gender = _chef_identity_cached(instance.actor, cache)
            data["actor_name"] = name
            data["actor_telegram_url"] = url
            data["actor_gender"] = gender
        return data


class CrmOrderClientSerializer(serializers.ModelSerializer):
    images = CrmOrderImageSerializer(many=True, read_only=True)
    cake_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    delivery_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    prepayment = serializers.DecimalField(max_digits=10, decimal_places=2)
    phones = serializers.SerializerMethodField()
    google_maps_url = serializers.SerializerMethodField()

    class Meta:
        model = CrmOrder
        fields = [
            "id",
            "date",
            "time_start",
            "time_end",
            "when_ready",
            "contact",
            "is_gift",
            "phones",
            "nickname",
            "delivery_address",
            "delivery_duration_seconds",
            "fulfillment_type",
            "status",
            "weight",
            "filling",
            "description",
            "cake_price",
            "delivery_price",
            "prepayment",
            "is_paid",
            "payment_type",
            "images",
            "google_maps_url",
        ]

    def get_google_maps_url(self, instance: CrmOrder) -> str | None:
        address = instance.delivery_address
        if not address:
            return None
        return cached_google_maps_url(address)

    def get_phones(self, instance: CrmOrder) -> list[dict[str, str | None]]:
        return order_phones(instance, self.context)


class CrmOrderUpdateSerializer(serializers.ModelSerializer):
    take_in_work = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = CrmOrder
        fields = ["status", "is_paid", "take_in_work", "payment_type"]

    def validate(self, attrs):
        if self.instance is not None and self.instance.status == CrmOrder.STATUS_UNCONFIRMED:
            if attrs.get("take_in_work"):
                raise serializers.ValidationError(
                    "Unconfirmed orders can only be moved to new."
                )
            status = attrs.get("status")
            if status is not None and status not in {
                CrmOrder.STATUS_UNCONFIRMED,
                CrmOrder.STATUS_NEW,
            }:
                raise serializers.ValidationError(
                    "Unconfirmed orders can only be moved to new."
                )
        return attrs

    def update(self, instance, validated_data):
        before = snapshot_crm_order(instance)
        previous_status = instance.status
        take_in_work = validated_data.pop("take_in_work", None)
        status = validated_data.pop("status", None)
        if take_in_work:
            instance.taken_by = self.context["request"].user
            if instance.status == CrmOrder.STATUS_NEW:
                instance.status = CrmOrder.STATUS_IN_WORK
        if status is not None:
            instance.status = status
            if (
                previous_status == CrmOrder.STATUS_UNCONFIRMED
                and status == CrmOrder.STATUS_NEW
                and instance.created_by_id is None
            ):
                instance.created_by = self.context["request"].user
            if status == CrmOrder.STATUS_NEW:
                instance.taken_by = None
            elif status == CrmOrder.STATUS_IN_WORK and instance.taken_by_id is None:
                instance.taken_by = self.context["request"].user
            if status == CrmOrder.STATUS_IN_DELIVERY:
                if instance.delivered_by_id is None:
                    instance.delivered_by = self.context["request"].user
            elif status == CrmOrder.STATUS_DELIVERED:
                instance.delivered_by = self.context["request"].user
            else:
                instance.delivered_by = None
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        sync_flowwow_order_status_from_crm(instance, previous_status)
        instance.save()
        record_crm_order_event(
            instance,
            CrmOrderEvent.ACTION_UPDATED,
            CrmOrderEvent.SOURCE_CRM,
            self.context["request"].user,
            before,
        )
        schedule_order_confirmed_email(instance, previous_status)
        return instance


class CrmOrderWriteSerializer(serializers.ModelSerializer):
    time_start = serializers.TimeField(allow_null=True, required=False)
    time_end = serializers.TimeField(allow_null=True, required=False)
    payment_date = serializers.DateField(allow_null=True, required=False)
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
    )
    delete_image_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
    )
    items = serializers.JSONField(binary=True, write_only=True, required=False)

    class Meta:
        model = CrmOrder
        fields = [
            "date",
            "time_start",
            "time_end",
            "when_ready",
            "contact",
            "is_gift",
            "nickname",
            "delivery_address",
            "fulfillment_type",
            "status",
            "weight",
            "filling",
            "description",
            "internal_description",
            "cake_price",
            "delivery_price",
            "prepayment",
            "is_paid",
            "payment_type",
            "payment_date",
            "images",
            "delete_image_ids",
            "items",
        ]

    def validate_items(self, value) -> list[dict]:
        serializer = CrmOrderItemInputSerializer(data=value, many=True)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def validate_delete_image_ids(self, value: list[int]) -> list[int]:
        if not self.instance:
            return value
        existing = set(self.instance.images.filter(id__in=value).values_list("id", flat=True))
        missing = set(value) - existing
        if missing:
            raise serializers.ValidationError("Unknown image ids.")
        return value

    def validate(self, attrs):
        if self.instance is not None and self.instance.status == CrmOrder.STATUS_UNCONFIRMED:
            status = attrs.get("status")
            if status is not None and status not in {
                CrmOrder.STATUS_UNCONFIRMED,
                CrmOrder.STATUS_NEW,
            }:
                raise serializers.ValidationError(
                    "Unconfirmed orders can only be moved to new."
                )
        return attrs

    def create(self, validated_data):
        images = validated_data.pop("images", [])
        validated_data.pop("delete_image_ids", None)
        items = validated_data.pop("items", None)
        validated_data["created_by"] = self.context["request"].user
        order = CrmOrder.objects.create(**validated_data)
        self._apply_images(order, images, [])
        if items is not None:
            replace_crm_order_items(order, items)
        record_crm_order_event(
            order,
            CrmOrderEvent.ACTION_CREATED,
            CrmOrderEvent.SOURCE_CRM,
            self.context["request"].user,
            None,
        )
        return order

    def update(self, instance, validated_data):
        before = snapshot_crm_order(instance)
        previous_status = instance.status
        images = validated_data.pop("images", [])
        delete_image_ids = validated_data.pop("delete_image_ids", [])
        items = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if (
            previous_status == CrmOrder.STATUS_UNCONFIRMED
            and instance.status == CrmOrder.STATUS_NEW
            and instance.created_by_id is None
        ):
            instance.created_by = self.context["request"].user
        sync_flowwow_order_status_from_crm(instance, previous_status)
        instance.save()
        self._apply_images(instance, images, delete_image_ids)
        if items is not None:
            replace_crm_order_items(instance, items)
        record_crm_order_event(
            instance,
            CrmOrderEvent.ACTION_UPDATED,
            CrmOrderEvent.SOURCE_CRM,
            self.context["request"].user,
            before,
        )
        schedule_order_confirmed_email(instance, previous_status)
        return instance

    def _apply_images(self, order: CrmOrder, images: list, delete_image_ids: list[int]) -> None:
        if delete_image_ids:
            CrmOrderImage.objects.filter(order=order, id__in=delete_image_ids).delete()
        kept = list(order.images.order_by("position", "id"))
        position = 0
        for img in kept:
            img.position = position
            img.save(update_fields=["position"])
            position += 1
        for image in images:
            CrmOrderImage.objects.create(order=order, image=image, position=position)
            position += 1


class ResolveYandexAddressSerializer(serializers.Serializer):
    address = serializers.CharField()


class ResolveGoogleAddressSerializer(serializers.Serializer):
    address = serializers.CharField()


class CrmOrderQuerySerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    month = serializers.RegexField(regex=r"^\d{4}-(0[1-9]|1[0-2])$", required=False)
    status = serializers.ChoiceField(choices=[CrmOrder.STATUS_UNCONFIRMED], required=False)

    def validate(self, attrs):
        if attrs.get("date") is not None and attrs.get("month") is not None:
            raise serializers.ValidationError("Pass either date or month, not both.")
        if attrs.get("status") and (attrs.get("date") is not None or attrs.get("month") is not None):
            raise serializers.ValidationError("Pass status alone.")
        return attrs


class CrmOrderMapQuerySerializer(serializers.Serializer):
    range = serializers.ChoiceField(choices=["next_3_hours", "today"], required=False)
    date = serializers.DateField(required=False)

    def validate(self, attrs):
        has_range = attrs.get("range") is not None
        has_date = attrs.get("date") is not None
        if has_range and has_date:
            raise serializers.ValidationError("Pass either range or date, not both.")
        if not has_range and not has_date:
            raise serializers.ValidationError("Pass either range or date.")
        return attrs


class CrmMapOrderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateField()
    time_start = serializers.TimeField(allow_null=True)
    time_end = serializers.TimeField(allow_null=True)
    when_ready = serializers.BooleanField()
    filling = serializers.CharField()
    weight = serializers.CharField()
    description = serializers.CharField()
    fulfillment_type = serializers.CharField()
    status = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    image = serializers.JSONField(allow_null=True)
    delivery_distance_meters = serializers.IntegerField(allow_null=True)
    delivery_duration_seconds = serializers.IntegerField(allow_null=True)


class CrmExpensesBreakdownSerializer(serializers.Serializer):
    salary = serializers.DecimalField(max_digits=10, decimal_places=2)
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)


class CrmExpensesDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    salary = serializers.DecimalField(max_digits=10, decimal_places=2)
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)


class CrmExpensesMonthSerializer(serializers.Serializer):
    month = serializers.CharField()
    salary = serializers.DecimalField(max_digits=10, decimal_places=2)
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    by_date = serializers.DictField(child=CrmExpensesBreakdownSerializer())


class CrmSalariesQuerySerializer(serializers.Serializer):
    month = serializers.RegexField(regex=r"^\d{4}-(0[1-9]|1[0-2])$", required=False)


class CrmSalaryEmployeeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    money = serializers.DecimalField(max_digits=10, decimal_places=2)


class CrmSalaryPeriodSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()
    employees = CrmSalaryEmployeeSerializer(many=True)
    total_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_money = serializers.DecimalField(max_digits=10, decimal_places=2)


class CrmSalariesSerializer(serializers.Serializer):
    month = serializers.CharField()
    periods = CrmSalaryPeriodSerializer(many=True)
    total_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_money = serializers.DecimalField(max_digits=10, decimal_places=2)


class FinanceTransactionsQuerySerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    month = serializers.RegexField(regex=r"^\d{4}-(0[1-9]|1[0-2])$", required=False)

    def validate(self, attrs):
        if attrs.get("date") is not None and attrs.get("month") is not None:
            raise serializers.ValidationError("Pass either date or month, not both.")
        return attrs


class FinanceTransactionAccountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    currency = serializers.CharField()


class FinanceTransactionAccountDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    kind = serializers.CharField()
    bank_name = serializers.CharField()
    iban = serializers.CharField()
    currency = serializers.CharField()


class FinanceTransactionMatchedSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    account = FinanceTransactionAccountSerializer()
    counterparty_name = serializers.CharField()
    description = serializers.CharField()


class FinanceTransactionCrmOrderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateField()
    contact = serializers.CharField()
    weight = serializers.CharField()
    filling = serializers.CharField()
    cake_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    delivery_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class FinanceTransactionWaybillSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    waybill_number = serializers.CharField()
    seller_name = serializers.CharField()
    seller_name_ru = serializers.CharField()
    full_amount = serializers.DecimalField(max_digits=14, decimal_places=4)
    create_date = serializers.DateTimeField()


class FinanceTransactionInvoiceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    series = serializers.CharField()
    number = serializers.CharField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=4)
    reg_dt = serializers.DateTimeField()


class FinanceTransactionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    kind = serializers.CharField()
    income_type = serializers.CharField()
    expense_type = serializers.CharField()
    account = FinanceTransactionAccountDetailSerializer()
    counterparty_name = serializers.CharField()
    counterparty_iban = serializers.CharField()
    description = serializers.CharField()
    external_id = serializers.CharField()
    transfer_id = serializers.UUIDField(allow_null=True)
    flowwow_order_number = serializers.SerializerMethodField()
    crm_orders = FinanceTransactionCrmOrderSerializer(many=True)
    waybills = FinanceTransactionWaybillSerializer(many=True)
    invoices = FinanceTransactionInvoiceSerializer(many=True)
    matched_account = FinanceTransactionAccountSerializer(
        source="matched_transaction.account",
        allow_null=True,
    )
    matched_transaction = FinanceTransactionMatchedSerializer(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_flowwow_order_number(self, obj: FinancialTransaction) -> int | None:
        if obj.account.name != FLOWWOW_ACCOUNT_NAME:
            return None
        segment, separator, _rest = obj.external_id.partition("|")
        if separator == "" or not segment.isdigit():
            return None
        return int(segment)


class FinanceTransactionsResponseSerializer(serializers.Serializer):
    date = serializers.DateField(allow_null=True)
    month = serializers.CharField(allow_null=True)
    transactions = FinanceTransactionSerializer(many=True)


class FinanceTransactionSearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(allow_blank=True)


class FinanceTransactionSearchSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    account = FinanceTransactionAccountSerializer()
    counterparty_name = serializers.CharField()
    description = serializers.CharField()


class FinanceTransactionCounterpartSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_account_id(self, value: int) -> int:
        if not FinancialAccount.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Unknown account.")
        return value


class FinanceTransactionWriteSerializer(serializers.Serializer):
    date = serializers.DateField()
    account_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    kind = serializers.ChoiceField(choices=FinancialTransaction.KIND_CHOICES)
    income_type = serializers.ChoiceField(
        choices=FinancialTransaction.INCOME_TYPE_CHOICES,
        allow_blank=True,
    )
    expense_type = serializers.ChoiceField(
        choices=FinancialTransaction.EXPENSE_TYPE_CHOICES,
        allow_blank=True,
    )
    counterparty_name = serializers.CharField(allow_blank=True, max_length=255)
    counterparty_iban = serializers.CharField(allow_blank=True, max_length=34)
    description = serializers.CharField(allow_blank=True)
    transfer_pair = serializers.ChoiceField(
        choices=[(PAIR_NONE, PAIR_NONE), (PAIR_LINK, PAIR_LINK), (PAIR_CREATE, PAIR_CREATE)]
    )
    matched_transaction_id = serializers.IntegerField(allow_null=True)
    counterpart = FinanceTransactionCounterpartSerializer(allow_null=True)

    def validate_account_id(self, value: int) -> int:
        if not FinancialAccount.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Unknown account.")
        return value

    def validate(self, attrs):
        kind = attrs["kind"]
        income_type = attrs["income_type"]
        expense_type = attrs["expense_type"]
        if kind == FinancialTransaction.KIND_INCOME:
            if expense_type != "":
                raise serializers.ValidationError(
                    {"expense_type": "Expense type is only allowed for expenses."}
                )
        elif kind == FinancialTransaction.KIND_EXPENSE:
            if income_type != "":
                raise serializers.ValidationError(
                    {"income_type": "Income type is only allowed for income."}
                )
        elif income_type != "" or expense_type != "":
            raise serializers.ValidationError(
                {"kind": "Income and expense types are only allowed for income and expense."}
            )
        pair = attrs["transfer_pair"]
        matched_id = attrs["matched_transaction_id"]
        counterpart = attrs["counterpart"]
        if kind != FinancialTransaction.KIND_TRANSFER:
            if pair != PAIR_NONE or matched_id is not None or counterpart is not None:
                raise serializers.ValidationError(
                    {"transfer_pair": "A pair is only allowed for transfers."}
                )
            return attrs
        if pair == PAIR_NONE:
            if matched_id is not None or counterpart is not None:
                raise serializers.ValidationError(
                    {"transfer_pair": "A transfer without a pair must not include a counterpart."}
                )
            return attrs
        if pair == PAIR_LINK:
            if counterpart is not None or matched_id is None:
                raise serializers.ValidationError(
                    {"matched_transaction_id": "Choose a transaction to link."}
                )
            if not FinancialTransaction.objects.filter(pk=matched_id).exists():
                raise serializers.ValidationError({"matched_transaction_id": "Unknown transaction."})
            if "transaction_id" in self.context and matched_id == self.context["transaction_id"]:
                raise serializers.ValidationError(
                    {"matched_transaction_id": "A transaction cannot be linked to itself."}
                )
            return attrs
        if matched_id is not None or counterpart is None:
            raise serializers.ValidationError({"counterpart": "Create the other side of the transfer."})
        if counterpart["account_id"] == attrs["account_id"]:
            raise serializers.ValidationError(
                {"counterpart": "The other side must use a different account."}
            )
        return attrs


class ExchangeRatesSerializer(serializers.Serializer):
    date = serializers.DateField()
    rates = serializers.DictField(child=serializers.CharField())
