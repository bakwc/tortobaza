from datetime import time, timedelta
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from crm.cash_transactions import sync_cash_paid_order_transactions
from crm.flowwow import sync_flowwow_orders
from crm.google_maps import (
    SWEET_CHILL_COORDS,
    coords_from_google_url,
    is_bakery_pickup_address,
    resolve_google_maps_url,
)
from crm.google_routes import compute_delivery_route
from crm.models import (
    CrmOrder,
    DeliveryRouteResolveFailure,
    GoogleAddressResolveFailure,
    ResolvedGoogleAddress,
    ResolvedTelegramPhone,
    ResolvedYandexAddress,
    YandexAddressResolveFailure,
)
from crm.telegram import crm_order_slot_datetime, sync_crm_order_to_telegram
from crm.telegram_user import pending_telegram_phones, resolve_phone
from crm.yandex_maps import resolve_yandex_maps_url

_TB = ZoneInfo("Asia/Tbilisi")

YANDEX_ADDRESS_RESOLVE_MAX_FAILURES = 3
GOOGLE_ADDRESS_RESOLVE_MAX_FAILURES = 3
ROUTE_RESOLVE_MAX_FAILURES = 3
TELEGRAM_PHONE_CHECKS_PER_SYNC = 5


class Command(BaseCommand):
    def handle(self, *args, **options):
        sync_flowwow_orders()
        now = timezone.now().astimezone(_TB)
        start = (now - timedelta(days=7)).date()
        end = now.date()
        if now.time() >= time(16, 0):
            end = now.date() + timedelta(days=1)
        blocked_addresses = YandexAddressResolveFailure.objects.filter(
            failure_count__gte=YANDEX_ADDRESS_RESOLVE_MAX_FAILURES,
        ).values("address")
        cached_addresses = ResolvedYandexAddress.objects.values("address")
        addresses = list(
            CrmOrder.objects.filter(
                deleted=False,
                fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
                date__gte=start,
                date__lte=end,
            )
            .exclude(delivery_address="")
            .exclude(delivery_address__in=cached_addresses)
            .exclude(delivery_address__in=blocked_addresses)
            .values_list("delivery_address", flat=True)
            .distinct()
        )
        for address in addresses:
            try:
                resolve_yandex_maps_url(address)
                YandexAddressResolveFailure.objects.filter(address=address).delete()
            except Exception:
                failure, created = YandexAddressResolveFailure.objects.get_or_create(
                    address=address,
                    defaults={"failure_count": 1},
                )
                if not created:
                    failure.failure_count += 1
                    failure.save(update_fields=["failure_count"])
        blocked_google_addresses = GoogleAddressResolveFailure.objects.filter(
            failure_count__gte=GOOGLE_ADDRESS_RESOLVE_MAX_FAILURES,
        ).values("address")
        cached_google_addresses = ResolvedGoogleAddress.objects.values("address")
        window_addresses = CrmOrder.objects.filter(
            deleted=False,
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            date__gte=start,
            date__lte=end,
        ).exclude(delivery_address="")
        google_rows = (
            ResolvedYandexAddress.objects.filter(
                address__in=window_addresses.values("delivery_address"),
            )
            .exclude(address__in=cached_google_addresses)
            .exclude(address__in=blocked_google_addresses)
        )
        for row in google_rows:
            try:
                resolve_google_maps_url(row.address, row.yandex_url)
                GoogleAddressResolveFailure.objects.filter(address=row.address).delete()
            except Exception:
                failure, created = GoogleAddressResolveFailure.objects.get_or_create(
                    address=row.address,
                    defaults={"failure_count": 1},
                )
                if not created:
                    failure.failure_count += 1
                    failure.save(update_fields=["failure_count"])
        google_urls = {
            row.address: row.google_url
            for row in ResolvedGoogleAddress.objects.filter(
                address__in=window_addresses.values("delivery_address"),
            )
        }
        blocked_route_order_ids = DeliveryRouteResolveFailure.objects.filter(
            failure_count__gte=ROUTE_RESOLVE_MAX_FAILURES,
        ).values("order_id")
        route_orders = (
            CrmOrder.objects.filter(
                deleted=False,
                fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
                date__gte=start,
                date__lte=end,
                when_ready=False,
                time_start__isnull=False,
            )
            .exclude(delivery_address="")
            .exclude(pk__in=blocked_route_order_ids)
        )
        for order in route_orders:
            if is_bakery_pickup_address(order.delivery_address):
                continue
            google_url = google_urls.get(order.delivery_address)
            if google_url is None:
                continue
            destination = coords_from_google_url(google_url)
            if destination is None:
                continue
            slot = crm_order_slot_datetime(order)
            if slot <= now:
                continue
            refresh_at = slot - timedelta(hours=1)
            first_compute = order.delivery_distance_meters is None
            refresh = (
                order.delivery_route_computed_at is not None
                and now >= refresh_at
                and order.delivery_route_computed_at < refresh_at
            )
            if not first_compute and not refresh:
                continue
            try:
                distance_meters, duration_seconds = compute_delivery_route(
                    SWEET_CHILL_COORDS,
                    destination,
                    slot,
                )
            except Exception:
                failure, created = DeliveryRouteResolveFailure.objects.get_or_create(
                    order=order,
                    defaults={"failure_count": 1},
                )
                if not created:
                    failure.failure_count += 1
                    failure.save(update_fields=["failure_count"])
                continue
            order.delivery_distance_meters = distance_meters
            order.delivery_duration_seconds = duration_seconds
            order.delivery_route_computed_at = timezone.now()
            order.save(
                update_fields=[
                    "delivery_distance_meters",
                    "delivery_duration_seconds",
                    "delivery_route_computed_at",
                    "updated_at",
                ]
            )
            DeliveryRouteResolveFailure.objects.filter(order=order).delete()
        order_ids = list(
            CrmOrder.objects.filter(
                Q(deleted=False, date__gte=start, date__lte=end)
                | Q(telegram_message_id__isnull=False, date__gte=start)
            ).values_list("pk", flat=True)
        )
        for order_id in order_ids:
            sync_crm_order_to_telegram(order_id)
        for number in pending_telegram_phones(TELEGRAM_PHONE_CHECKS_PER_SYNC):
            result = resolve_phone(number)
            username = result["username"]
            ResolvedTelegramPhone.objects.create(
                number=result["number"],
                resolved=result["resolved"],
                user_id=result["user_id"],
                username="" if username is None else username,
            )
        sync_cash_paid_order_transactions()
