from rest_framework import serializers

from accounts.models import chef_identity
from catalog.responsive_urls import detail_image
from crm.flowwow import sync_flowwow_order_status_from_crm
from crm.google_maps import cached_google_maps_url
from crm.history import USER_ID_FIELDS, record_crm_order_event, snapshot_crm_order
from crm.models import CrmOrder, CrmOrderEvent, CrmOrderImage
from crm.phone import links_for_stored
from orders.email import schedule_order_confirmed_email


class CrmOrderImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = CrmOrderImage
        fields = ["id", "image", "position"]

    def get_image(self, obj: CrmOrderImage) -> dict[str, str]:
        public_base_url = self.context["request"].build_absolute_uri("/").rstrip("/")
        return detail_image(obj.image.name, public_base_url)


class CrmOrderSerializer(serializers.ModelSerializer):
    images = CrmOrderImageSerializer(many=True, read_only=True)
    cake_price = serializers.DecimalField(max_digits=10, decimal_places=2)
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
            "phones",
            "nickname",
            "delivery_address",
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
            "prepayment",
            "is_paid",
            "payment_type",
            "created_at",
            "updated_at",
            "images",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
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
        phones: list[dict[str, str | None]] = []
        for phone in instance.phones:
            links = links_for_stored(phone["value"])
            links["party"] = phone["party"]
            phones.append(links)
        return phones


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
            "phones",
            "nickname",
            "delivery_address",
            "fulfillment_type",
            "status",
            "weight",
            "filling",
            "description",
            "cake_price",
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
        phones: list[dict[str, str | None]] = []
        for phone in instance.phones:
            links = links_for_stored(phone["value"])
            links["party"] = phone["party"]
            phones.append(links)
        return phones


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
                and status != CrmOrder.STATUS_UNCONFIRMED
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

    class Meta:
        model = CrmOrder
        fields = [
            "date",
            "time_start",
            "time_end",
            "when_ready",
            "contact",
            "nickname",
            "delivery_address",
            "fulfillment_type",
            "status",
            "weight",
            "filling",
            "description",
            "internal_description",
            "cake_price",
            "prepayment",
            "is_paid",
            "payment_type",
            "images",
            "delete_image_ids",
        ]

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
        validated_data["created_by"] = self.context["request"].user
        order = CrmOrder.objects.create(**validated_data)
        self._apply_images(order, images, [])
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

    def validate(self, attrs):
        if attrs.get("date") is not None and attrs.get("month") is not None:
            raise serializers.ValidationError("Pass either date or month, not both.")
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
