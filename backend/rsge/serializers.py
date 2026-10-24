from rest_framework import serializers

from rsge.models import Invoice, InvoiceLine, Waybill, WaybillGood


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


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "rs_id",
            "goods",
            "unit",
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
            "notes",
            "amount",
            "vat",
            "k_id",
            "agree_date",
            "agree_s_user_id",
            "ref_date",
            "ref_s_user_id",
            "note",
            "lines",
        ]
