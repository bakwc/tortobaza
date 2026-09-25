import json
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import (
    SAFE_METHODS,
    AllowAny,
    BasePermission,
    IsAdminUser,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.salary import compute_all_salaries
from catalog.responsive_urls import detail_image
from crm.flowwow import log_webhook, process_flowwow_webhook, verify_webhook_signature
from crm.google_maps import coords_for_map_order, resolve_google_maps_url
from crm.history import USER_ID_FIELDS, record_crm_order_event, snapshot_crm_order
from crm.models import CrmOrder, CrmOrderEvent, FlowwowWebhookEvent, ResolvedGoogleAddress
from crm.rent import daily_rent, monthly_rent
from crm.serializers import (
    CrmExpensesDaySerializer,
    CrmExpensesMonthSerializer,
    CrmMapOrderSerializer,
    CrmOrderClientSerializer,
    CrmOrderEventSerializer,
    CrmOrderMapQuerySerializer,
    CrmOrderQuerySerializer,
    CrmOrderSerializer,
    CrmOrderUpdateSerializer,
    CrmOrderWriteSerializer,
    ResolveGoogleAddressSerializer,
    ResolveYandexAddressSerializer,
)
from crm.telegram import schedule_crm_order_telegram_sync
from crm.website import sync_website_order_status_from_crm
from crm.yandex_maps import resolve_yandex_maps_url

_TB = ZoneInfo("Asia/Tbilisi")


class CrmOrderWritePermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        if request.method == "PATCH":
            return set(request.data.keys()) <= {"status", "take_in_work"}
        return False


def live_orders():
    return CrmOrder.objects.filter(deleted=False).select_related(
        "taken_by", "created_by", "delivered_by"
    )


def _tbilisi_now() -> datetime:
    return timezone.now().astimezone(_TB)


def _slot_overlaps_window(order: CrmOrder, window_start: datetime, window_end: datetime) -> bool:
    start = datetime.combine(order.date, order.time_start, tzinfo=_TB)
    end_time = order.time_end if order.time_end is not None else order.time_start
    end = datetime.combine(order.date, end_time, tzinfo=_TB)
    return start <= window_end and end >= window_start


def _map_orders_queryset(range_key: str | None, now: datetime, target_date: date | None):
    today = now.date()
    orders = live_orders().prefetch_related("images")
    if range_key == "next_3_hours":
        until = now + timedelta(hours=3)
        return orders.filter(date__in={today, until.date()}).filter(
            when_ready=False,
            time_start__isnull=False,
        ).exclude(time_start=time(0, 0))
    day = target_date if target_date is not None else today
    return orders.filter(date=day)


def _map_order_payloads(orders, range_key: str | None, now: datetime, public_base_url: str) -> list[dict]:
    until = now + timedelta(hours=3)
    candidates = []
    for order in orders:
        if range_key == "next_3_hours" and not _slot_overlaps_window(order, now, until):
            continue
        candidates.append(order)
    addresses = [order.delivery_address for order in candidates if order.delivery_address]
    cached = {
        row.address: row.google_url
        for row in ResolvedGoogleAddress.objects.filter(address__in=addresses)
    }
    payloads = []
    for order in candidates:
        address = order.delivery_address
        pair = coords_for_map_order(address, order.fulfillment_type, cached.get(address))
        if pair is None:
            continue
        images = list(order.images.all())
        image = None
        if images:
            image = detail_image(images[0].image.name, public_base_url)
        payloads.append(
            {
                "id": order.id,
                "date": order.date,
                "time_start": order.time_start,
                "time_end": order.time_end,
                "when_ready": order.when_ready,
                "filling": order.filling,
                "weight": order.weight,
                "description": order.description,
                "fulfillment_type": order.fulfillment_type,
                "status": order.status,
                "lat": pair[0],
                "lng": pair[1],
                "image": image,
            }
        )
    return payloads


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
        order_status = query_serializer.validated_data.get("status")
        if order_status == CrmOrder.STATUS_UNCONFIRMED:
            orders = live_orders().filter(
                status=CrmOrder.STATUS_UNCONFIRMED,
            ).prefetch_related("images")
            serializer = CrmOrderSerializer(orders, many=True, context={"request": request})
            return Response({"orders": serializer.data})
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


class CrmOrderMapView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query_serializer = CrmOrderMapQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        range_key = query_serializer.validated_data.get("range")
        target_date = query_serializer.validated_data.get("date")
        now = _tbilisi_now()
        orders = _map_orders_queryset(range_key, now, target_date)
        public_base_url = request.build_absolute_uri("/").rstrip("/")
        payloads = _map_order_payloads(orders, range_key, now, public_base_url)
        serializer = CrmMapOrderSerializer(payloads, many=True)
        response_range = range_key if range_key is not None else "today"
        return Response({"range": response_range, "orders": serializer.data})


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
        sync_website_order_status_from_crm(order)
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
        sync_website_order_status_from_crm(order)
        schedule_crm_order_telegram_sync(order.pk)
        return Response(CrmOrderSerializer(order, context={"request": request}).data)

    def delete(self, request, pk: int):
        order = get_object_or_404(live_orders(), pk=pk)
        before = snapshot_crm_order(order)
        order.deleted = True
        order.save(update_fields=["deleted", "updated_at"])
        record_crm_order_event(
            order,
            CrmOrderEvent.ACTION_DELETED,
            CrmOrderEvent.SOURCE_CRM,
            request.user,
            before,
        )
        schedule_crm_order_telegram_sync(order.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CrmOrderEventsView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, CrmOrderWritePermission]

    def get(self, request, pk: int):
        order = get_object_or_404(live_orders(), pk=pk)
        events = list(order.events.select_related("actor"))
        user_ids: set[int] = set()
        for event in events:
            for field in USER_ID_FIELDS:
                change = event.changes.get(field)
                if change is None:
                    continue
                if change["old"] is not None:
                    user_ids.add(change["old"])
                if change["new"] is not None:
                    user_ids.add(change["new"])
        users_by_id = {user.id: user for user in User.objects.filter(id__in=user_ids)}
        serializer = CrmOrderEventSerializer(
            events,
            many=True,
            context={"request": request, "users_by_id": users_by_id, "identities": {}},
        )
        return Response(serializer.data)


def _client_no_store_headers(response: Response) -> Response:
    response["Cache-Control"] = "private, no-store, no-cache, must-revalidate"
    response["Pragma"] = "no-cache"
    response["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet, noimageindex"
    return response


class CrmOrderClientView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, token: str):
        order = get_object_or_404(
            live_orders().prefetch_related("images"),
            client_token=token,
        )
        return _client_no_store_headers(
            Response(CrmOrderClientSerializer(order, context={"request": request}).data)
        )


class CrmOrderClientMapView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, token: str):
        order = get_object_or_404(live_orders(), client_token=token)
        address = order.delivery_address
        if not address:
            return _client_no_store_headers(Response(status=status.HTTP_404_NOT_FOUND))
        yandex_url = resolve_yandex_maps_url(address)
        url = resolve_google_maps_url(address, yandex_url)
        return _client_no_store_headers(Response({"url": url}))


class ResolveYandexAddressView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ResolveYandexAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url = resolve_yandex_maps_url(serializer.validated_data["address"])
        return Response({"url": url})


class ResolveGoogleAddressView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ResolveGoogleAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = serializer.validated_data["address"]
        yandex_url = resolve_yandex_maps_url(address)
        url = resolve_google_maps_url(address, yandex_url)
        return Response({"url": url})


class CrmExpensesView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        query_serializer = CrmOrderQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        month = query_serializer.validated_data.get("month")
        if month:
            year_str, month_str = month.split("-")
            year = int(year_str)
            month_num = int(month_str)
            start_date = date(year, month_num, 1)
            end_date = date(year, month_num, monthrange(year, month_num)[1])
            result = compute_all_salaries(start_date, end_date)
            rent_day = daily_rent(start_date)
            serializer = CrmExpensesMonthSerializer(
                {
                    "month": month,
                    "salary": result["total_money"],
                    "rent": monthly_rent(),
                    "by_date": {
                        day.isoformat(): {"salary": money, "rent": rent_day}
                        for day, money in result["by_date"].items()
                    },
                }
            )
            return Response(serializer.data)
        target_date = query_serializer.validated_data.get("date") or timezone.now().astimezone(
            _TB
        ).date()
        result = compute_all_salaries(target_date, target_date)
        serializer = CrmExpensesDaySerializer(
            {
                "date": target_date,
                "salary": result["total_money"],
                "rent": daily_rent(target_date),
            }
        )
        return Response(serializer.data)


@method_decorator(csrf_exempt, name="dispatch")
class FlowwowWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        body = request.body
        signature = request.headers.get("X-Webhook-Signature")
        if not verify_webhook_signature(body, signature):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        uuid_value = payload.get("uuid")
        if not uuid_value:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if FlowwowWebhookEvent.objects.filter(uuid=uuid_value).exists():
            return Response(status=status.HTTP_200_OK)
        log_webhook(payload, body)
        process_flowwow_webhook(payload)
        FlowwowWebhookEvent.objects.get_or_create(uuid=uuid_value)
        return Response(status=status.HTTP_200_OK)
