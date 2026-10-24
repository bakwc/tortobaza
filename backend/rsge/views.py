from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.views import IsFinanceAdmin
from rsge.client import (
    call_accept_invoice,
    call_chek,
    call_confirm_waybill,
    call_ref_invoice,
    call_reject_waybill,
)
from rsge.models import Invoice, Waybill
from rsge.serializers import (
    InvoiceRejectSerializer,
    InvoiceSerializer,
    MonthQuerySerializer,
    WaybillSerializer,
)

_TB = ZoneInfo("Asia/Tbilisi")
ACCEPT_TARGET = {1: 2, 5: 8, 6: 7}


def _month_bounds(month: str) -> tuple[datetime, datetime]:
    year_str, month_str = month.split("-")
    year = int(year_str)
    month_num = int(month_str)
    start = datetime(year, month_num, 1, tzinfo=_TB)
    if month_num == 12:
        end = datetime(year + 1, 1, 1, tzinfo=_TB)
    else:
        end = datetime(year, month_num + 1, 1, tzinfo=_TB)
    return start, end


class WaybillListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def get(self, request):
        query = MonthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        start, end = _month_bounds(query.validated_data["month"])
        waybills = Waybill.objects.prefetch_related(
            "goods",
            "invoices",
            "financial_transactions",
        ).filter(
            create_date__gte=start,
            create_date__lt=end,
        )
        return Response(WaybillSerializer(waybills, many=True).data)


def rs_credentials() -> tuple[str, str]:
    su = settings.RS_SU
    sp = settings.RS_SP
    if su == "" or sp == "":
        raise RuntimeError("RS_SU and RS_SP are required")
    return su, sp


def waybill_for_decision(pk: int) -> Waybill:
    return get_object_or_404(
        Waybill.objects.prefetch_related("goods", "invoices", "financial_transactions"),
        pk=pk,
    )


class WaybillConfirmView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def post(self, request, pk: int):
        waybill = waybill_for_decision(pk)
        su, sp = rs_credentials()
        call_confirm_waybill(su, sp, str(waybill.rs_id))
        waybill.is_confirmed = 1
        waybill.save(update_fields=["is_confirmed"])
        return Response(WaybillSerializer(waybill).data)


class WaybillRejectView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def post(self, request, pk: int):
        waybill = waybill_for_decision(pk)
        su, sp = rs_credentials()
        call_reject_waybill(su, sp, str(waybill.rs_id))
        waybill.is_confirmed = -1
        waybill.save(update_fields=["is_confirmed"])
        return Response(WaybillSerializer(waybill).data)


class InvoiceListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def get(self, request):
        query = MonthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        start, end = _month_bounds(query.validated_data["month"])
        invoices = Invoice.objects.prefetch_related(
            "lines",
            "waybills",
            "financial_transactions",
        ).filter(
            reg_dt__gte=start,
            reg_dt__lt=end,
        )
        return Response(InvoiceSerializer(invoices, many=True).data)


def invoice_for_decision(pk: int) -> Invoice:
    invoice = get_object_or_404(
        Invoice.objects.prefetch_related("lines", "waybills", "financial_transactions"),
        pk=pk,
    )
    if invoice.status not in ACCEPT_TARGET or invoice.was_ref != 0:
        raise RuntimeError(
            f"invoice {invoice.rs_id} status {invoice.status} cannot be decided"
        )
    return invoice


class InvoiceConfirmView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def post(self, request, pk: int):
        invoice = invoice_for_decision(pk)
        su, sp = rs_credentials()
        user_id = call_chek(su, sp)
        target = ACCEPT_TARGET[invoice.status]
        call_accept_invoice(su, sp, user_id, str(invoice.rs_id), str(target))
        invoice.status = target
        invoice.agree_date = timezone.now()
        invoice.save(update_fields=["status", "agree_date"])
        return Response(InvoiceSerializer(invoice).data)


class InvoiceRejectView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def post(self, request, pk: int):
        body = InvoiceRejectSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        invoice = invoice_for_decision(pk)
        su, sp = rs_credentials()
        user_id = call_chek(su, sp)
        call_ref_invoice(su, sp, user_id, str(invoice.rs_id), body.validated_data["ref_text"])
        invoice.was_ref = 1
        invoice.ref_date = timezone.now()
        invoice.save(update_fields=["was_ref", "ref_date"])
        return Response(InvoiceSerializer(invoice).data)
