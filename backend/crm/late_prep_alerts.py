import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import UserProfile, chef_identity
from crm.models import CrmOrder
from crm.telegram import _telegram_json, crm_order_prep_datetime, sync_crm_order_to_telegram

_TB = ZoneInfo("Asia/Tbilisi")
_DONE = (
    CrmOrder.STATUS_READY,
    CrmOrder.STATUS_CLIENT_APPROVED,
    CrmOrder.STATUS_IN_DELIVERY,
    CrmOrder.STATUS_DELIVERED,
)


def schedule_crm_order_telegram_sync(order_id: int) -> None:
    transaction.on_commit(
        lambda: threading.Thread(
            target=sync_order_telegram_and_late_prep,
            args=(order_id,),
            daemon=True,
        ).start()
    )


def sync_order_telegram_and_late_prep(order_id: int) -> None:
    sync_crm_order_to_telegram(order_id)
    refresh_order_late_prep(order_id, timezone.now())


def notify_late_preps(now: datetime) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CRM_CHAT_ID
    if not token or not chat_id:
        return
    now_tb = now.astimezone(_TB)
    cooking = (
        CrmOrder.STATUS_UNCONFIRMED,
        CrmOrder.STATUS_NEW,
        CrmOrder.STATUS_IN_WORK,
    )
    order_ids = CrmOrder.objects.filter(deleted=False, late_prep_closed=False).filter(
        Q(
            status__in=cooking,
            when_ready=False,
            time_start__isnull=False,
            date__gte=now_tb.date() - timedelta(days=7),
            date__lte=now_tb.date() + timedelta(days=1),
        )
        | Q(late_prep_message_id__isnull=False)
    ).values_list("pk", flat=True)
    for order_id in order_ids:
        refresh_order_late_prep(order_id, now)


def refresh_order_late_prep(order_id: int, now: datetime) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CRM_CHAT_ID
    if not token or not chat_id:
        return
    with transaction.atomic():
        order = CrmOrder.objects.select_for_update().select_related("taken_by").get(pk=order_id)
        _refresh_locked(order, now, chat_id)


def _refresh_locked(order: CrmOrder, now: datetime, chat_id: str) -> None:
    if order.late_prep_closed or order.deleted:
        return
    prep = crm_order_prep_datetime(order)
    done = order.status in _DONE
    muted = _cook_skips(order)
    late = prep is not None and now >= prep
    if order.late_prep_message_id is not None and not late:
        _telegram_json(
            "deleteMessage",
            {"chat_id": chat_id, "message_id": order.late_prep_message_id},
        )
        order.late_prep_message_id = None
        order.save(update_fields=["late_prep_message_id", "updated_at"])
        return
    if prep is None or not late:
        return
    if order.late_prep_message_id is None:
        if done or muted:
            return
        result = _telegram_json(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": _message(order, now, prep),
                "disable_web_page_preview": True,
            },
        )
        order.late_prep_message_id = result["result"]["message_id"]
        order.save(update_fields=["late_prep_message_id", "updated_at"])
        return
    if muted and not done:
        return
    if muted and done:
        order.late_prep_closed = True
        order.save(update_fields=["late_prep_closed", "updated_at"])
        return
    _telegram_json(
        "editMessageText",
        {
            "chat_id": chat_id,
            "message_id": order.late_prep_message_id,
            "text": _message(order, now, prep),
            "disable_web_page_preview": True,
        },
    )
    if done:
        order.late_prep_closed = True
        order.save(update_fields=["late_prep_closed", "updated_at"])


def _cook_skips(order: CrmOrder) -> bool:
    if order.taken_by_id is None:
        return False
    return UserProfile.objects.filter(user_id=order.taken_by_id, skip_late_alerts=True).exists()


def _minutes_phrase(minutes: int) -> str:
    n = minutes % 100
    if 11 <= n <= 14:
        word = "минут"
    elif n % 10 == 1:
        word = "минуту"
    elif 2 <= n % 10 <= 4:
        word = "минуты"
    else:
        word = "минут"
    return f"{minutes} {word}"


def _message(order: CrmOrder, now: datetime, prep: datetime) -> str:
    minutes = max(1, int((now - prep).total_seconds() // 60))
    clock = prep.astimezone(_TB).strftime("%H:%M")
    if order.taken_by_id is None:
        cook = "никто не готовит"
    else:
        name, _url, _nick, _gender = chef_identity(order.taken_by)
        cook = f"готовит {name}"
    return (
        f"Опоздание по заказу #{order.pk} на {_minutes_phrase(minutes)} - "
        f"должен был быть приготовлен к {clock}, {cook}"
    )
