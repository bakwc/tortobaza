import hashlib
import html
import json
import threading
import urllib.error
import urllib.request
import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import chef_identity
from crm.models import CrmOrder, CrmOrderImage
from crm.phone import contact_links
from crm.yandex_maps import cached_yandex_maps_url

_TB = ZoneInfo("Asia/Tbilisi")

_PAYMENT_LABELS = {
    CrmOrder.PAYMENT_UNKNOWN: "Неизвестно",
    CrmOrder.PAYMENT_CASH: "Наличные",
    CrmOrder.PAYMENT_TERMINAL: "Терминал",
    CrmOrder.PAYMENT_TBC: "TBC",
    CrmOrder.PAYMENT_BOG: "BOG",
    CrmOrder.PAYMENT_FLOWWOW: "Flowwow",
    CrmOrder.PAYMENT_CRYPTO: "Криптовалюта",
    CrmOrder.PAYMENT_ONLINE: "Онлайн на сайте",
}

_FULFILLMENT_LABELS = {
    CrmOrder.FULFILLMENT_DELIVERY: "Доставка",
    CrmOrder.FULFILLMENT_PICKUP: "Самовывоз",
}


def _esc(value: str) -> str:
    return html.escape(value, quote=False)


def crm_order_slot_datetime(order: CrmOrder) -> datetime:
    if order.time_start is None:
        return datetime.combine(order.date, time(0, 0), tzinfo=_TB)
    slot = datetime.combine(order.date, order.time_start, tzinfo=_TB)
    if order.time_start == time(0, 0):
        return slot + timedelta(days=1)
    return slot


def crm_order_in_telegram_window(order: CrmOrder, now: datetime) -> bool:
    slot = crm_order_slot_datetime(order)
    now_tb = now.astimezone(_TB)
    last_allowed_date = now_tb.date()
    if now_tb.time() >= time(16, 0):
        last_allowed_date = now_tb.date() + timedelta(days=1)
    return now_tb - timedelta(days=7) <= slot and order.date <= last_allowed_date


def build_crm_order_telegram_payload(order: CrmOrder) -> dict:
    images = [[img.id, img.position] for img in order.images.all()]
    payload = {
        "cake_price": str(order.cake_price),
        "contact": order.contact,
        "contact_e164": None,
        "date": order.date.isoformat(),
        "deleted": order.deleted,
        "delivery_address": order.delivery_address,
        "description": order.description,
        "filling": order.filling,
        "fulfillment_type": order.fulfillment_type,
        "images": images,
        "is_delivered": order.is_delivered,
        "is_delivered_mark": "✅" if order.is_delivered else "❌",
        "is_paid": order.is_paid,
        "nickname": order.nickname,
        "payment_type": order.payment_type,
        "prepayment": str(order.prepayment),
        "taken_by_name": None,
        "taken_by_telegram_url": None,
        "time_end": order.time_end.isoformat() if order.time_end is not None else None,
        "time_start": order.time_start.isoformat() if order.time_start is not None else None,
        "weight": order.weight,
        "when_ready": order.when_ready,
    }
    links = contact_links(order.contact)
    if links is not None:
        payload["contact_e164"] = links["e164"]
    if order.taken_by_id:
        name, url = chef_identity(order.taken_by)
        payload["taken_by_name"] = name
        payload["taken_by_telegram_url"] = url
    if not order.is_delivered:
        payload["take_in_work_url"] = _crm_order_take_url(order)
    if order.fulfillment_type == CrmOrder.FULFILLMENT_DELIVERY and order.delivery_address:
        yandex_url = cached_yandex_maps_url(order.delivery_address)
        if yandex_url:
            payload["yandex_url"] = yandex_url
    return payload


def crm_order_telegram_hash(order: CrmOrder) -> str:
    payload = build_crm_order_telegram_payload(order)
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _format_money(amount: Decimal) -> str:
    return f"{amount:.2f} ₾"


def _format_slot(order: CrmOrder) -> str:
    date_part = order.date.strftime("%d.%m.%Y")
    if order.when_ready:
        return f"{date_part}, по готовности"
    if order.time_start is None:
        return f"{date_part}, время не указано"
    start = order.time_start.strftime("%H:%M")
    if order.time_end is not None:
        return f"{date_part}, {start} – {order.time_end.strftime('%H:%M')}"
    return f"{date_part}, {start}"


def _format_slot_short(order: CrmOrder) -> str:
    date_part = order.date.strftime("%d.%m")
    if order.when_ready:
        return f"{date_part}, по готовности"
    if order.time_start is None:
        return f"{date_part}, время не указано"
    start = order.time_start.strftime("%H:%M")
    if order.time_end is not None:
        return f"{date_part} {start}–{order.time_end.strftime('%H:%M')}"
    return f"{date_part} {start}"


def _crm_order_view_url(order: CrmOrder) -> str:
    return f"{settings.SITE_URL}/ru/crm?date={order.date.isoformat()}&order={order.pk}"


def _crm_order_edit_url(order: CrmOrder) -> str:
    return f"{settings.SITE_URL}/ru/crm/{order.pk}/edit"


def _crm_order_take_url(order: CrmOrder) -> str:
    return f"{settings.SITE_URL}/ru/crm/{order.pk}/take"


def build_crm_order_telegram_html(order: CrmOrder) -> str:
    lines = []
    if order.deleted:
        lines.append("<b>ОТМЕНЁН</b>")
        lines.append("")
    lines.append(f"<b>CRM заказ #{order.pk}</b>")
    view_href = html.escape(_crm_order_view_url(order), quote=True)
    edit_href = html.escape(_crm_order_edit_url(order), quote=True)
    if order.is_delivered:
        lines.append(f'<a href="{view_href}">смотреть</a> · <a href="{edit_href}">редактировать</a>')
    else:
        take_href = html.escape(_crm_order_take_url(order), quote=True)
        lines.append(
            f'<a href="{view_href}">смотреть</a> · <a href="{edit_href}">редактировать</a> · '
            f'<a href="{take_href}">взять в работу</a>'
        )
    lines.append("")
    lines.append(f"<b>Время:</b> {_esc(_format_slot(order))}")
    lines.append(f"<b>Тип:</b> {_FULFILLMENT_LABELS[order.fulfillment_type]}")
    if order.fulfillment_type == CrmOrder.FULFILLMENT_DELIVERY and order.delivery_address:
        yandex_url = cached_yandex_maps_url(order.delivery_address)
        if yandex_url:
            href = html.escape(yandex_url, quote=True)
            lines.append(f'<b>Адрес:</b> <a href="{href}">{_esc(order.delivery_address)}</a>')
        else:
            lines.append(f"<b>Адрес:</b> {_esc(order.delivery_address)}")
    lines.append(f"<b>Контакт:</b> {_esc(order.contact)}")
    links = contact_links(order.contact)
    if links is not None:
        lines.append(_esc(links["e164"]))
        wa_href = html.escape(links["whatsapp"], quote=True)
        lines.append(f'<a href="{wa_href}">WhatsApp</a>')
    if order.nickname:
        lines.append(f"<b>Ник:</b> {_esc(order.nickname)}")
    lines.append(f"<b>Вес:</b> {_esc(order.weight)}")
    lines.append(f"<b>Начинка:</b> {_esc(order.filling)}")
    if order.description:
        lines.append(f"<b>Описание:</b> {_esc(order.description)}")
    lines.append(f"<b>Цена:</b> {_format_money(order.cake_price)}")
    lines.append(f"<b>Предоплата:</b> {_format_money(order.prepayment)}")
    lines.append(f"<b>Оплата:</b> {_PAYMENT_LABELS[order.payment_type]}")
    lines.append(f"<b>Оплачен:</b> {'да' if order.is_paid else 'нет'}")
    lines.append(f"<b>Доставлен / выдан:</b> {'✅' if order.is_delivered else '❌'}")
    if order.taken_by_id:
        name, url = chef_identity(order.taken_by)
        if url:
            href = html.escape(url, quote=True)
            lines.append(f'<b>Готовит шеф</b> <a href="{href}">@{_esc(name)}</a>')
        else:
            lines.append(f"<b>Готовит шеф</b> {_esc(name)}")
    return "\n".join(lines)


def _channel_message_link(chat_id: str, message_id: int) -> str:
    raw = str(chat_id)
    if raw.startswith("-100"):
        internal = raw[4:]
    else:
        internal = raw.lstrip("-")
    return f"https://t.me/c/{internal}/{message_id}"


def _urlopen_with_retry(req: urllib.request.Request):
    for attempt in range(3):
        try:
            return urllib.request.urlopen(req, timeout=60)
        except urllib.error.HTTPError:
            raise
        except (TimeoutError, urllib.error.URLError):
            if attempt == 2:
                raise


def _telegram_json(method: str, payload: dict) -> dict:
    token = settings.TELEGRAM_BOT_TOKEN
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with _urlopen_with_retry(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if method != "editMessageText" or exc.code != 400:
            raise
        data = json.loads(exc.read().decode("utf-8"))
        if "message is not modified" not in data["description"]:
            raise
        return data
    if not data["ok"]:
        raise RuntimeError(data)
    return data


def _telegram_multipart(method: str, fields: dict[str, str], files: list[tuple[str, str, bytes]]) -> dict:
    token = settings.TELEGRAM_BOT_TOKEN
    boundary = uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")
    for field_name, filename, content in files:
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
        )
        body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
        body.extend(content)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with _urlopen_with_retry(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not data["ok"]:
        raise RuntimeError(data)
    return data


def _read_image(img: CrmOrderImage) -> tuple[str, bytes]:
    img.image.open("rb")
    content = img.image.read()
    img.image.close()
    return Path(img.image.name).name, content


def _media_message_ids(raw: list) -> list[int]:
    ids = []
    for item in raw:
        if isinstance(item, dict):
            ids.append(int(item["message_id"]))
        else:
            ids.append(int(item))
    return ids


def _media_image_ids(raw: list) -> list[int]:
    ids = []
    for item in raw:
        if isinstance(item, dict) and "image_id" in item:
            ids.append(int(item["image_id"]))
    return ids


def _post_photos(order: CrmOrder, chat_id: str) -> list[dict]:
    images = list(order.images.all())
    posted: list[dict] = []
    for i in range(0, len(images), 10):
        chunk = images[i : i + 10]
        if len(chunk) == 1:
            img = chunk[0]
            name, content = _read_image(img)
            result = _telegram_multipart(
                "sendPhoto",
                {"chat_id": chat_id},
                [("photo", name, content)],
            )
            posted.append({"message_id": result["result"]["message_id"], "image_id": img.id})
            continue
        files = []
        media = []
        for idx, img in enumerate(chunk):
            name, content = _read_image(img)
            attach = f"file{idx}"
            files.append((attach, name, content))
            media.append({"type": "photo", "media": f"attach://{attach}"})
        result = _telegram_multipart(
            "sendMediaGroup",
            {"chat_id": chat_id, "media": json.dumps(media)},
            files,
        )
        for img, item in zip(chunk, result["result"], strict=True):
            posted.append({"message_id": item["message_id"], "image_id": img.id})
    return posted


def _delete_media(chat_id: str, media: list) -> None:
    for message_id in _media_message_ids(media):
        _telegram_json("deleteMessage", {"chat_id": chat_id, "message_id": message_id})


def _slot_tuple(order: CrmOrder) -> tuple:
    return (order.date, order.time_start, order.time_end, order.when_ready)


def _posted_slot_tuple(order: CrmOrder) -> tuple:
    return (
        order.telegram_posted_date,
        order.telegram_posted_time_start,
        order.telegram_posted_time_end,
        order.telegram_posted_when_ready,
    )


def _persist_telegram_state(order: CrmOrder, message_id: int, media: list, payload_hash: str) -> None:
    order.telegram_message_id = message_id
    order.telegram_media_ids = media
    order.telegram_payload_hash = payload_hash
    order.telegram_posted_date = order.date
    order.telegram_posted_time_start = order.time_start
    order.telegram_posted_time_end = order.time_end
    order.telegram_posted_when_ready = order.when_ready
    order.save(
        update_fields=[
            "telegram_message_id",
            "telegram_media_ids",
            "telegram_payload_hash",
            "telegram_posted_date",
            "telegram_posted_time_start",
            "telegram_posted_time_end",
            "telegram_posted_when_ready",
            "updated_at",
        ]
    )


def sync_crm_order_to_telegram(order_id: int) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CRM_CHAT_ID
    if not token or not chat_id:
        return
    with transaction.atomic():
        order = CrmOrder.objects.select_for_update().select_related("taken_by").get(pk=order_id)
        list(order.images.all())
        new_hash = crm_order_telegram_hash(order)
        posted_before = order.telegram_message_id is not None
        if posted_before and order.telegram_payload_hash == new_hash:
            return
        if not posted_before:
            if order.deleted:
                return
            now = timezone.now()
            if not crm_order_in_telegram_window(order, now):
                return
            media = _post_photos(order, chat_id)
            text_result = _telegram_json(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": build_crm_order_telegram_html(order),
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            _persist_telegram_state(
                order,
                text_result["result"]["message_id"],
                media,
                new_hash,
            )
            return
        current_image_ids = [img.id for img in order.images.all()]
        stored_image_ids = _media_image_ids(order.telegram_media_ids)
        if current_image_ids != stored_image_ids:
            _delete_media(chat_id, order.telegram_media_ids)
            media = _post_photos(order, chat_id)
        else:
            media = order.telegram_media_ids
        _telegram_json(
            "editMessageText",
            {
                "chat_id": chat_id,
                "message_id": order.telegram_message_id,
                "text": build_crm_order_telegram_html(order),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        slot_changed = _slot_tuple(order) != _posted_slot_tuple(order)
        if slot_changed:
            link = _channel_message_link(chat_id, order.telegram_message_id)
            _telegram_json(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": (
                        f"время доставки / выдачи поменялось на {_esc(_format_slot_short(order))}\n"
                        f'<a href="{link}">исходное сообщение</a>'
                    ),
                    "parse_mode": "HTML",
                    "reply_to_message_id": order.telegram_message_id,
                    "disable_web_page_preview": True,
                },
            )
        _persist_telegram_state(order, order.telegram_message_id, media, new_hash)


def schedule_crm_order_telegram_sync(order_id: int) -> None:
    transaction.on_commit(
        lambda: threading.Thread(
            target=sync_crm_order_to_telegram,
            args=(order_id,),
            daemon=True,
        ).start()
    )
