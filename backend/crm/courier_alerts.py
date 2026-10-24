import math
from datetime import datetime, timedelta

import requests
from django.conf import settings

from accounts.models import UserProfile
from crm.models import CrmOrder
from crm.telegram import crm_order_departure_datetime

_PUSHOVER_MESSAGES_URL = "https://api.pushover.net/1/messages.json"
_ALERT_BEFORE = timedelta(minutes=20)
_ALERT_AFTER = timedelta(hours=6)
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
        if now < departure - _ALERT_BEFORE or now >= departure + _ALERT_AFTER:
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
    if remaining > timedelta(0):
        minutes = math.ceil(remaining.total_seconds() / 60)
        title = f"Выезд через {minutes} мин"
    else:
        title = "Выезд просрочен"
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
            "title": title,
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
