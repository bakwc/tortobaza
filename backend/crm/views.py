from zoneinfo import ZoneInfo

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import CrmOrder
from crm.serializers import (
    CrmOrderQuerySerializer,
    CrmOrderSerializer,
    CrmOrderUpdateSerializer,
    CrmOrderWriteSerializer,
    ResolveYandexAddressSerializer,
)
from crm.telegram import schedule_crm_order_telegram_sync
from crm.yandex_maps import resolve_yandex_maps_url

_TB = ZoneInfo("Asia/Tbilisi")


class CrmOrderWritePermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        if request.method == "PATCH":
            return set(request.data.keys()) <= {"is_delivered", "take_in_work"}
        return False


def live_orders():
    return CrmOrder.objects.filter(deleted=False).select_related("taken_by")


def crm_order_write_payload(request):
    payload = {}
    for key in request.data:
        if key in ("images", "delete_image_ids"):
            continue
        payload[key] = request.data.get(key)
    if payload.get("time_start") == "":
        payload["time_start"] = None
    if payload.get("time_end") == "":
        payload["time_end"] = None
    payload["images"] = request.FILES.getlist("images")
    payload["delete_image_ids"] = request.data.getlist("delete_image_ids")
    return payload


class CrmOrderListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, CrmOrderWritePermission]

    def get(self, request):
        query_serializer = CrmOrderQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        month = query_serializer.validated_data.get("month")
        if month:
            year_str, month_str = month.split("-")
            orders = live_orders().filter(
                date__year=int(year_str),
                date__month=int(month_str),
            ).prefetch_related("images")
            serializer = CrmOrderSerializer(orders, many=True, context={"request": request})
            return Response(
                {
                    "month": month,
                    "orders": serializer.data,
                }
            )
        target_date = query_serializer.validated_data.get("date") or timezone.now().astimezone(_TB).date()
        orders = live_orders().filter(date=target_date).prefetch_related("images")
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
        schedule_crm_order_telegram_sync(order.pk)
        order = live_orders().prefetch_related("images").get(pk=order.pk)
        return Response(
            CrmOrderSerializer(order, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CrmOrderDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, CrmOrderWritePermission]

    def get(self, request, pk: int):
        order = get_object_or_404(live_orders().prefetch_related("images"), pk=pk)
        return Response(CrmOrderSerializer(order, context={"request": request}).data)

    def put(self, request, pk: int):
        order = get_object_or_404(live_orders().prefetch_related("images"), pk=pk)
        serializer = CrmOrderWriteSerializer(
            order,
            data=crm_order_write_payload(request),
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        schedule_crm_order_telegram_sync(order.pk)
        order = live_orders().prefetch_related("images").get(pk=order.pk)
        return Response(CrmOrderSerializer(order, context={"request": request}).data)

    def patch(self, request, pk: int):
        order = get_object_or_404(live_orders().prefetch_related("images"), pk=pk)
        serializer = CrmOrderUpdateSerializer(
            order,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        schedule_crm_order_telegram_sync(order.pk)
        return Response(CrmOrderSerializer(order, context={"request": request}).data)

    def delete(self, request, pk: int):
        order = get_object_or_404(live_orders(), pk=pk)
        order.deleted = True
        order.save(update_fields=["deleted", "updated_at"])
        schedule_crm_order_telegram_sync(order.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResolveYandexAddressView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ResolveYandexAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url = resolve_yandex_maps_url(serializer.validated_data["address"])
        return Response({"url": url})
