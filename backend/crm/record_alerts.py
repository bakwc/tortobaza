import threading
from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

from crm.models import CrmOrder
from crm.telegram import _telegram_json

_TB = ZoneInfo("Asia/Tbilisi")


def schedule_monthly_record_notification(order_id: int) -> None:
    transaction.on_commit(
        lambda: threading.Thread(
            target=notify_monthly_record,
            args=(order_id,),
            daemon=True,
        ).start()
    )


def notify_monthly_record(order_id: int) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CRM_CHAT_ID
    if not token or not chat_id:
        return
    order = CrmOrder.objects.get(pk=order_id)
    if order.deleted:
        return
    today = timezone.now().astimezone(_TB).date()
    if order.date.year != today.year or order.date.month != today.month:
        return
    current, record = _month_counts(today)
    if record is None:
        return
    remaining = record - current
    if remaining < 1 or remaining > 9:
        return
    _telegram_json(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": _message(remaining, current, record),
            "disable_web_page_preview": True,
        },
    )


def _month_counts(today: date) -> tuple[int, int | None]:
    current_start = date(today.year, today.month, 1)
    current = 0
    record = None
    rows = (
        CrmOrder.objects.filter(deleted=False)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Count("id"))
    )
    for row in rows:
        month = _as_date(row["month"])
        total = row["total"]
        if month.year == today.year and month.month == today.month:
            current = total
        elif month < current_start:
            if record is None or total > record:
                record = total
    return current, record


def _as_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


def _message(remaining: int, current: int, record: int) -> str:
    if remaining == 1:
        return f"до рекорда остался 1 заказ ({current} из {record})"
    if remaining < 5:
        return f"до рекорда осталось {remaining} заказа ({current} из {record})"
    return f"до рекорда осталось {remaining} заказов ({current} из {record})"
