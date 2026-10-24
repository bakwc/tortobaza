from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rsge.models import Invoice, Waybill
from rsge.serializers import InvoiceSerializer, WaybillSerializer


class WaybillListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        waybills = Waybill.objects.prefetch_related("goods").all()
        return Response(WaybillSerializer(waybills, many=True).data)


class InvoiceListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        invoices = Invoice.objects.prefetch_related("lines").all()
        return Response(InvoiceSerializer(invoices, many=True).data)
