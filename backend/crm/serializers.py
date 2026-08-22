from rest_framework import serializers

from catalog.responsive_urls import detail_image
from crm.models import CrmOrder, CrmOrderImage


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

    class Meta:
        model = CrmOrder
        fields = [
            "id",
            "date",
            "time_start",
            "time_end",
            "contact",
            "fulfillment_type",
            "is_delivered",
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


class CrmOrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrmOrder
        fields = ["is_delivered", "is_paid"]


class CrmOrderQuerySerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
