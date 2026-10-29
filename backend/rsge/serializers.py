from decimal import Decimal

from rest_framework import serializers

from menu.models import Ingredient
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


class LinkedTransactionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    counterparty_name = serializers.CharField()


class LinkedWaybillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Waybill
        fields = [
            "id",
            "waybill_number",
            "seller_name",
            "seller_name_ru",
            "full_amount",
            "create_date",
        ]


class LinkedInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "series", "number", "amount", "reg_dt"]


class WaybillSupplyLineSerializer(serializers.Serializer):
    good_id = serializers.IntegerField()
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all(), allow_null=True)
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
        allow_null=True,
    )
    skipped = serializers.BooleanField()

    def validate(self, attrs):
        if attrs["skipped"]:
            if attrs["ingredient"] is not None or attrs["quantity"] is not None:
                raise serializers.ValidationError("A skipped line has no ingredient or quantity.")
            return attrs
        if attrs["ingredient"] is None or attrs["quantity"] is None:
            raise serializers.ValidationError("Choose an ingredient and a quantity.")
        return attrs


class WaybillSupplyCreateSerializer(serializers.Serializer):
    lines = WaybillSupplyLineSerializer(many=True)


class WaybillSerializer(serializers.ModelSerializer):
    goods = WaybillGoodSerializer(many=True)
    invoices = LinkedInvoiceSerializer(many=True)
    financial_transactions = LinkedTransactionSerializer(many=True)
    supply_id = serializers.IntegerField(allow_null=True, read_only=True)
    supply = serializers.SerializerMethodField()

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
            "invoices",
            "financial_transactions",
            "supply_id",
            "supply",
        ]

    def get_supply(self, waybill: Waybill) -> dict | None:
        if waybill.supply_id is None:
            return None
        row = waybill.supply
        total = sum((line.total for line in row.lines.all()), Decimal("0"))
        return {"id": row.pk, "date": row.date.isoformat(), "total": str(total)}


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
    waybills = LinkedWaybillSerializer(many=True)
    financial_transactions = LinkedTransactionSerializer(many=True)

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
            "waybills",
            "financial_transactions",
        ]
