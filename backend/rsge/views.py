from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.views import IsFinanceAdmin
from rsge.models import Invoice, Waybill
from rsge.serializers import InvoiceSerializer, WaybillSerializer


class WaybillListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def get(self, request):
        waybills = Waybill.objects.prefetch_related("goods").all()
        return Response(WaybillSerializer(waybills, many=True).data)


class InvoiceListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def get(self, request):
        invoices = Invoice.objects.prefetch_related("lines").all()
        return Response(InvoiceSerializer(invoices, many=True).data)
