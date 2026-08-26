from datetime import timedelta
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone

from crm.models import CrmOrder
from crm.telegram import sync_crm_order_to_telegram

_TB = ZoneInfo("Asia/Tbilisi")


class Command(BaseCommand):
    def handle(self, *args, **options):
        now = timezone.now().astimezone(_TB)
        start = (now - timedelta(days=7)).date()
        end = (now + timedelta(hours=24)).date()
        order_ids = list(
            CrmOrder.objects.filter(
                telegram_message_id__isnull=True,
                deleted=False,
                date__gte=start,
                date__lte=end,
            ).values_list("pk", flat=True)
        )
        for order_id in order_ids:
            sync_crm_order_to_telegram(order_id)
