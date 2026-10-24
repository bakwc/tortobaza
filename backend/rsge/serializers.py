from rest_framework import serializers

from rsge.models import Waybill, WaybillGood


class WaybillGoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaybillGood
        fields = [
            "id",
            "rs_id",
            "name",
            "unit_id",
            "unit_txt",
            "quantity",
            "price",
            "amount",
            "bar_code",
            "a_id",
            "vat_type",
            "quantity_ext",
            "status",
            "quantity_f",
        ]


class WaybillSerializer(serializers.ModelSerializer):
    goods = WaybillGoodSerializer(many=True)

    class Meta:
        model = Waybill
        fields = [
            "id",
            "rs_id",
            "waybill_number",
            "type",
            "status",
            "create_date",
            "activate_date",
            "begin_date",
            "delivery_date",
            "close_date",
            "buyer_tin",
            "buyer_name",
            "seller_tin",
            "seller_name",
            "start_address",
            "end_address",
            "driver_tin",
            "driver_name",
            "car_number",
            "reception_info",
            "waybill_comment",
            "transport_coast",
            "full_amount",
            "s_user_id",
            "par_id",
            "invoice_id",
            "is_confirmed",
            "is_corrected",
            "seller_st",
            "is_med",
            "goods",
        ]
