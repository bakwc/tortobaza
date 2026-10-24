import math
from datetime import datetime, timedelta

import requests
from django.conf import settings

from accounts.models import UserProfile
from crm.models import CrmOrder
from crm.telegram import crm_order_departure_datetime

_PUSHOVER_MESSAGES_URL = "https://api.pushover.net/1/messages.json"
_ALERT_WINDOW = timedelta(minutes=20)
_SKIP_STATUSES = (
    CrmOrder.STATUS_UNCONFIRMED,
    CrmOrder.STATUS_IN_DELIVERY,
    CrmOrder.STATUS_DELIVERED,
)


def notify_courier_departures(now: datetime) -> None:
    couriers = list(
        UserProfile.objects.filter(is_active_courier=True).exclude(pushover_user="")
    )
    if not couriers:
        return
    orders = CrmOrder.objects.filter(
        deleted=False,
        fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
        when_ready=False,
        time_start__isnull=False,
    ).exclude(status__in=_SKIP_STATUSES)
    for order in orders:
        departure = crm_order_departure_datetime(order)
        if departure is None:
            continue
        remaining = departure - now
        if not (timedelta(0) < remaining <= _ALERT_WINDOW):
            continue
        if order.courier_alerted_departure_at == departure:
            continue
        for profile in couriers:
            _send_departure_alert(profile.pushover_user, order, departure, remaining)
        order.courier_alerted_departure_at = departure
        order.save(update_fields=["courier_alerted_departure_at", "updated_at"])


def _send_departure_alert(
    user_key: str,
    order: CrmOrder,
    departure: datetime,
    remaining: timedelta,
) -> None:
    minutes = math.ceil(remaining.total_seconds() / 60)
    start = order.time_start.strftime("%H:%M")
    if order.time_end is not None:
        slot = f"{start} – {order.time_end.strftime('%H:%M')}"
    else:
        slot = start
    message = "\n".join(
        [
            f"Заказ #{order.pk}",
            f"Адрес: {order.delivery_address}",
            f"Выезд: {departure.strftime('%H:%M')}",
            f"Доставка: {slot}",
        ]
    )
    response = requests.post(
        _PUSHOVER_MESSAGES_URL,
        data={
            "token": settings.PUSHOVER_API_TOKEN,
            "user": user_key,
            "title": f"Выезд через {minutes} мин",
            "message": message,
            "url": f"{settings.SITE_URL}/ru/crm?date={order.date.isoformat()}&order={order.pk}",
            "url_title": "Открыть заказ",
            "priority": "2",
            "sound": "siren",
            "retry": "60",
            "expire": "3600",
        },
        timeout=20,
    )
    response.raise_for_status()
