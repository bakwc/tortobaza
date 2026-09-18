from rest_framework import serializers

from accounts.models import chef_identity
from catalog.responsive_urls import detail_image
from crm.google_maps import cached_google_maps_url
from crm.models import CrmOrder, CrmOrderImage
from crm.phone import contact_links


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
    contact_tel = serializers.CharField(read_only=True, allow_null=True)
    contact_whatsapp = serializers.CharField(read_only=True, allow_null=True)
    contact_telegram = serializers.CharField(read_only=True, allow_null=True)
    taken_by_name = serializers.CharField(read_only=True, allow_null=True)
    taken_by_telegram_url = serializers.CharField(read_only=True, allow_null=True)
    taken_by_gender = serializers.CharField(read_only=True, allow_null=True)
    created_by_name = serializers.CharField(read_only=True, allow_null=True)
    created_by_telegram_url = serializers.CharField(read_only=True, allow_null=True)
    created_by_gender = serializers.CharField(read_only=True, allow_null=True)

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
            "contact_tel",
            "contact_whatsapp",
            "contact_telegram",
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
        links = contact_links(instance.contact)
        if links is None:
            data["contact_tel"] = None
            data["contact_whatsapp"] = None
            data["contact_telegram"] = None
            return data
        data["contact_tel"] = links["tel"]
        data["contact_whatsapp"] = links["whatsapp"]
        data["contact_telegram"] = links["telegram"]
        return data


class CrmOrderClientSerializer(serializers.ModelSerializer):
    images = CrmOrderImageSerializer(many=True, read_only=True)
    cake_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    prepayment = serializers.DecimalField(max_digits=10, decimal_places=2)
    contact_tel = serializers.CharField(read_only=True, allow_null=True)
    contact_whatsapp = serializers.CharField(read_only=True, allow_null=True)
    contact_telegram = serializers.CharField(read_only=True, allow_null=True)
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
            "contact_tel",
            "contact_whatsapp",
            "contact_telegram",
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        links = contact_links(instance.contact)
        if links is None:
            data["contact_tel"] = None
            data["contact_whatsapp"] = None
            data["contact_telegram"] = None
            return data
        data["contact_tel"] = links["tel"]
        data["contact_whatsapp"] = links["whatsapp"]
        data["contact_telegram"] = links["telegram"]
        return data


class CrmOrderUpdateSerializer(serializers.ModelSerializer):
    take_in_work = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = CrmOrder
        fields = ["status", "is_paid", "take_in_work", "payment_type"]

    def update(self, instance, validated_data):
        take_in_work = validated_data.pop("take_in_work", None)
        status = validated_data.pop("status", None)
        if take_in_work:
            instance.taken_by = self.context["request"].user
            if instance.status == CrmOrder.STATUS_NEW:
                instance.status = CrmOrder.STATUS_IN_WORK
        if status is not None:
            instance.status = status
            if status == CrmOrder.STATUS_NEW:
                instance.taken_by = None
            elif status == CrmOrder.STATUS_IN_WORK and instance.taken_by_id is None:
                instance.taken_by = self.context["request"].user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.promote_if_paid()
        instance.save()
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

    def create(self, validated_data):
        images = validated_data.pop("images", [])
        validated_data.pop("delete_image_ids", None)
        validated_data["created_by"] = self.context["request"].user
        order = CrmOrder.objects.create(**validated_data)
        self._apply_images(order, images, [])
        return order

    def update(self, instance, validated_data):
        images = validated_data.pop("images", [])
        delete_image_ids = validated_data.pop("delete_image_ids", [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.promote_if_paid()
        instance.save()
        self._apply_images(instance, images, delete_image_ids)
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
