from datetime import time, timedelta
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone

from crm.models import CrmOrder, ResolvedYandexAddress, YandexAddressResolveFailure
from crm.telegram import sync_crm_order_to_telegram
from crm.yandex_maps import resolve_yandex_maps_url

_TB = ZoneInfo("Asia/Tbilisi")

YANDEX_ADDRESS_RESOLVE_MAX_FAILURES = 3


class Command(BaseCommand):
    def handle(self, *args, **options):
        now = timezone.now().astimezone(_TB)
        start = (now - timedelta(days=7)).date()
        end = now.date()
        if now.time() >= time(12, 0):
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
        order_ids = list(
            CrmOrder.objects.filter(
                deleted=False,
                date__gte=start,
                date__lte=end,
            ).values_list("pk", flat=True)
        )
        for order_id in order_ids:
            sync_crm_order_to_telegram(order_id)
