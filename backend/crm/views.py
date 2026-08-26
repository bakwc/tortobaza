from zoneinfo import ZoneInfo

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import CrmOrder
from crm.serializers import (
    CrmOrderQuerySerializer,
    CrmOrderSerializer,
    CrmOrderUpdateSerializer,
    CrmOrderWriteSerializer,
)

_TB = ZoneInfo("Asia/Tbilisi")


def crm_order_write_payload(request):
    payload = {}
    for key in request.data:
        if key in ("images", "delete_image_ids"):
            continue
        payload[key] = request.data.get(key)
    if payload.get("time_end") == "":
        payload["time_end"] = None
    payload["images"] = request.FILES.getlist("images")
    payload["delete_image_ids"] = request.data.getlist("delete_image_ids")
    return payload


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

    def post(self, request):
        serializer = CrmOrderWriteSerializer(
            data=crm_order_write_payload(request),
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        order = CrmOrder.objects.prefetch_related("images").get(pk=order.pk)
        return Response(
            CrmOrderSerializer(order, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CrmOrderDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        order = get_object_or_404(CrmOrder.objects.prefetch_related("images"), pk=pk)
        return Response(CrmOrderSerializer(order, context={"request": request}).data)

    def put(self, request, pk: int):
        order = get_object_or_404(CrmOrder.objects.prefetch_related("images"), pk=pk)
        serializer = CrmOrderWriteSerializer(
            order,
            data=crm_order_write_payload(request),
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        order = CrmOrder.objects.prefetch_related("images").get(pk=order.pk)
        return Response(CrmOrderSerializer(order, context={"request": request}).data)

    def patch(self, request, pk: int):
        order = get_object_or_404(CrmOrder.objects.prefetch_related("images"), pk=pk)
        serializer = CrmOrderUpdateSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CrmOrderSerializer(order, context={"request": request}).data)
