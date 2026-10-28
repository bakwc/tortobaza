from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.views import IsFinanceAdmin
from inventory.models import Supply
from inventory.serializers import SupplySerializer
from inventory.views import supplies_queryset
from inventory.waybill_supply import create_waybill_supply, supply_draft
from menu.views import serializer_context
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
    WaybillSupplyCreateSerializer,
)

_TB = ZoneInfo("Asia/Tbilisi")
ACCEPT_TARGET = {1: 2, 5: 8, 6: 7}
PENDING_INVOICE_STATUSES = (1, 5, 6)
PENDING_WINDOW = timedelta(days=30)


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


def waybill_queryset():
    return Waybill.objects.annotate(
        supply_id=Subquery(Supply.objects.filter(waybill_id=OuterRef("pk")).values("pk")[:1])
    ).prefetch_related("goods", "invoices", "financial_transactions")


class WaybillListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def get(self, request):
        query = MonthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        start, end = _month_bounds(query.validated_data["month"])
        waybills = waybill_queryset().filter(create_date__gte=start, create_date__lt=end)
        return Response(WaybillSerializer(waybills, many=True).data)


def rs_credentials() -> tuple[str, str]:
    su = settings.RS_SU
    sp = settings.RS_SP
    if su == "" or sp == "":
        raise RuntimeError("RS_SU and RS_SP are required")
    return su, sp


def waybill_for_decision(pk: int) -> Waybill:
    return get_object_or_404(waybill_queryset(), pk=pk)


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


class WaybillSupplyDraftView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def post(self, request, pk: int):
        waybill = waybill_for_decision(pk)
        return Response(supply_draft(waybill))


class WaybillSupplyCreateView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    @transaction.atomic
    def post(self, request, pk: int):
        waybill = waybill_for_decision(pk)
        serializer = WaybillSupplyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        supply = create_waybill_supply(waybill, serializer.validated_data["lines"], request.user)
        stored = supplies_queryset().get(pk=supply.pk)
        payload = SupplySerializer(stored, context=serializer_context(request))
        return Response(payload.data, status=status.HTTP_201_CREATED)


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


class PendingCountView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def get(self, request):
        cutoff = timezone.now() - PENDING_WINDOW
        waybills = Waybill.objects.filter(is_confirmed=0, create_date__gte=cutoff)
        invoices = Invoice.objects.filter(
            status__in=PENDING_INVOICE_STATUSES,
            was_ref=0,
            reg_dt__gte=cutoff,
        )
        oldest_waybill = waybills.order_by("create_date").values_list("create_date", flat=True).first()
        if oldest_waybill is not None:
            moment = oldest_waybill
            section = "waybills"
        else:
            oldest_invoice = invoices.order_by("reg_dt").values_list("reg_dt", flat=True).first()
            if oldest_invoice is None:
                return Response({"count": 0, "section": "", "month": ""})
            moment = oldest_invoice
            section = "invoices"
        local = moment.astimezone(_TB)
        month = f"{local.year:04d}-{local.month:02d}"
        return Response({"count": waybills.count() + invoices.count(), "section": section, "month": month})


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
