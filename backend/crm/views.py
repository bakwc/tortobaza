from zoneinfo import ZoneInfo

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import CrmOrder
from crm.serializers import (
    CrmOrderQuerySerializer,
    CrmOrderSerializer,
    CrmOrderUpdateSerializer,
)

_TB = ZoneInfo("Asia/Tbilisi")


class CrmOrderListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query_serializer = CrmOrderQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        target_date = query_serializer.validated_data.get("date") or timezone.now().astimezone(_TB).date()
        orders = CrmOrder.objects.filter(date=target_date).prefetch_related("images")
        serializer = CrmOrderSerializer(orders, many=True, context={"request": request})
        return Response(
            {
                "date": target_date.isoformat(),
                "orders": serializer.data,
            }
        )


class CrmOrderDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk: int):
        order = get_object_or_404(CrmOrder.objects.prefetch_related("images"), pk=pk)
        serializer = CrmOrderUpdateSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CrmOrderSerializer(order, context={"request": request}).data)
