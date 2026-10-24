from datetime import datetime
from zoneinfo import ZoneInfo

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.views import IsFinanceAdmin
from rsge.models import Invoice, Waybill
from rsge.serializers import InvoiceSerializer, MonthQuerySerializer, WaybillSerializer

_TB = ZoneInfo("Asia/Tbilisi")


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
        waybills = Waybill.objects.prefetch_related("goods").filter(
            create_date__gte=start,
            create_date__lt=end,
        )
        return Response(WaybillSerializer(waybills, many=True).data)


class InvoiceListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def get(self, request):
        query = MonthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        start, end = _month_bounds(query.validated_data["month"])
        invoices = Invoice.objects.prefetch_related("lines").filter(
            reg_dt__gte=start,
            reg_dt__lt=end,
        )
        return Response(InvoiceSerializer(invoices, many=True).data)
