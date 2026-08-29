from rest_framework import serializers

from accounts.models import chef_identity
from catalog.responsive_urls import detail_image
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
            "is_delivered",
            "taken_by_name",
            "taken_by_telegram_url",
            "weight",
            "filling",
            "description",
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
            name, url = chef_identity(instance.taken_by)
            data["taken_by_name"] = name
            data["taken_by_telegram_url"] = url
        else:
            data["taken_by_name"] = None
            data["taken_by_telegram_url"] = None
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
        fields = ["is_delivered", "is_paid", "take_in_work"]

    def update(self, instance, validated_data):
        take_in_work = validated_data.pop("take_in_work", None)
        if take_in_work:
            instance.taken_by = self.context["request"].user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
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
            "is_delivered",
            "weight",
            "filling",
            "description",
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
        order = CrmOrder.objects.create(**validated_data)
        self._apply_images(order, images, [])
        return order

    def update(self, instance, validated_data):
        images = validated_data.pop("images", [])
        delete_image_ids = validated_data.pop("delete_image_ids", [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
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
