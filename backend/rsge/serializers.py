from rest_framework import serializers

from rsge.models import Invoice, InvoiceLine, Waybill, WaybillGood


class MonthQuerySerializer(serializers.Serializer):
    month = serializers.RegexField(regex=r"^\d{4}-(0[1-9]|1[0-2])$")


class InvoiceRejectSerializer(serializers.Serializer):
    ref_text = serializers.CharField(allow_blank=False, trim_whitespace=True)


class WaybillGoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaybillGood
        fields = [
            "id",
            "rs_id",
            "name",
            "name_ru",
            "unit_id",
            "unit_txt",
            "unit_txt_ru",
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
            "buyer_name_ru",
            "seller_tin",
            "seller_name",
            "seller_name_ru",
            "start_address",
            "start_address_ru",
            "end_address",
            "end_address_ru",
            "driver_tin",
            "driver_name",
            "driver_name_ru",
            "car_number",
            "reception_info",
            "reception_info_ru",
            "waybill_comment",
            "waybill_comment_ru",
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


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "rs_id",
            "goods",
            "goods_ru",
            "unit",
            "unit_ru",
            "quantity",
            "full_amount",
            "vat_amount",
            "excise_amount",
            "excise_id",
            "waybill_id",
            "vat_type",
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "rs_id",
            "seller_un_id",
            "seq_num_b",
            "status",
            "was_ref",
            "series",
            "number",
            "reg_dt",
            "operation_dt",
            "s_user_id",
            "b_s_user_id",
            "doc_mos_nom",
            "seller_tin",
            "org_name",
            "org_name_ru",
            "notes",
            "notes_ru",
            "amount",
            "vat",
            "k_id",
            "agree_date",
            "agree_s_user_id",
            "ref_date",
            "ref_s_user_id",
            "note",
            "note_ru",
            "lines",
        ]
