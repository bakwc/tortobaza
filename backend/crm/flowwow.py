import hashlib
import hmac
import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from crm.models import CrmOrder, CrmOrderImage
from crm.telegram import schedule_crm_order_telegram_sync

logger = logging.getLogger(__name__)

_TB = ZoneInfo("Asia/Tbilisi")
_ORDERS_LIST_URL = "https://apis.flowwow.com/apiseller/orders/list"
_ORDERS_VIEW_URL = "https://apis.flowwow.com/apiseller/orders/view"
_PRODUCT_TYPE_ADDITIONAL = 3
_DELIVERY_TYPE_PICKUP = 4
_DELIVERY_TIME_ASAP = 1
_DELIVERY_TIME_INTERVAL = 2
_FILLING_PROPERTY_ID = 45
_FILLING_PROPERTY_TITLES = frozenset({"filling", "flavor", "начинка", "вкус"})
_WEIGHT_PROPERTY_TITLES = frozenset({"weight", "size", "вес", "размер"})
_WEIGHT_RE = re.compile(
    r"(?<!\w)\d+(?:[.,]\d+)?\s*"
    r"(?:килограмм(?:а|ов)?|кг|грамм(?:а|ов)?|гр|г|kilograms?|kgs?|kg|grams?|gr|g)"
    r"(?!\w)",
    re.IGNORECASE,
)


def verify_webhook_signature(body: bytes, header: str | None) -> bool:
    secret = settings.FLOWWOW_WEBHOOK_SECRET
    if not secret:
        return False
    if header is None or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(header, expected)


def log_webhook(payload: dict, body: bytes) -> None:
    order = payload.get("order") or {}
    logger.info(
        "flowwow webhook uuid=%s event=%s shopId=%s order.id=%s body=%s",
        payload.get("uuid"),
        payload.get("event"),
        payload.get("shopId"),
        order.get("id"),
        body.decode("utf-8"),
    )


def process_flowwow_webhook(payload: dict) -> None:
    event = payload["event"]
    if event == "order.paid":
        item = _fetch_order(payload["order"]["id"])
        crm_order = _upsert_crm_order(item)
        schedule_crm_order_telegram_sync(crm_order.pk)
        return
    if event == "order.cancelled":
        item = _fetch_order(payload["order"]["id"])
        crm_order = _upsert_crm_order(item)
        crm_order.deleted = True
        crm_order.save(update_fields=["deleted", "updated_at"])
        schedule_crm_order_telegram_sync(crm_order.pk)


def sync_flowwow_orders() -> None:
    now = timezone.now().astimezone(_TB)
    cutoff = now - timedelta(hours=24)
    cutoff_ts = int(cutoff.timestamp())
    items = _fetch_orders()
    logger.info(
        "flowwow sync now=%s cutoff=%s fetched=%s",
        now.isoformat(),
        cutoff.isoformat(),
        len(items),
    )
    print(
        f"flowwow sync now={now.isoformat()} cutoff={cutoff.isoformat()} fetched={len(items)}",
        flush=True,
    )
    kept: list[dict] = []
    for item in items:
        created = datetime.fromtimestamp(item["createdDate"], tz=_TB)
        delivery = datetime.fromtimestamp(item["deliveryDateFrom"], tz=_TB)
        logger.info(
            "flowwow order id=%s created=%s delivery_date=%s status=%s",
            item["id"],
            created.isoformat(),
            delivery.date().isoformat(),
            item["status"],
        )
        print(
            f"flowwow order id={item['id']} created={created.isoformat()} "
            f"delivery_date={delivery.date().isoformat()} status={item['status']}",
            flush=True,
        )
        if item["createdDate"] < cutoff_ts and item["deliveryDateFrom"] < cutoff_ts:
            logger.info(
                "flowwow order id=%s skipped created and delivery older than 24h",
                item["id"],
            )
            print(
                f"flowwow order id={item['id']} skipped created and delivery older than 24h",
                flush=True,
            )
            continue
        kept.append(item)
    logger.info("flowwow after filter kept=%s skipped=%s", len(kept), len(items) - len(kept))
    print(
        f"flowwow after filter kept={len(kept)} skipped={len(items) - len(kept)}",
        flush=True,
    )
    for item in kept:
        _upsert_crm_order(item)


def _fetch_orders() -> list[dict]:
    shop_id = int(settings.FLOWWOW_SHOP_ID.strip('"'))
    token = settings.FLOWWOW_API_TOKEN.strip('"')
    logger.info("flowwow fetch shopId=%s", shop_id)
    print(f"flowwow fetch shopId={shop_id}", flush=True)
    response = requests.get(
        _ORDERS_LIST_URL,
        params={"shopId": shop_id},
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "*/*",
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    items = payload["items"]
    logger.info("flowwow response total=%s items=%s", payload.get("total"), len(items))
    print(f"flowwow response total={payload.get('total')} items={len(items)}", flush=True)
    return items


def _fetch_order(order_id: int) -> dict:
    shop_id = int(settings.FLOWWOW_SHOP_ID.strip('"'))
    token = settings.FLOWWOW_API_TOKEN.strip('"')
    logger.info("flowwow fetch order shopId=%s orderId=%s", shop_id, order_id)
    print(f"flowwow fetch order shopId={shop_id} orderId={order_id}", flush=True)
    response = requests.get(
        _ORDERS_VIEW_URL,
        params={"shopId": shop_id, "orderId": order_id},
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "*/*",
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def _upsert_crm_order(item: dict) -> CrmOrder:
    fields = _crm_fields(item)
    crm_order = CrmOrder.objects.filter(flowwow_order_id=item["id"]).first()
    if crm_order is None:
        crm_order = CrmOrder.objects.create(
            flowwow_order_id=item["id"],
            status=CrmOrder.STATUS_NEW,
            **fields,
        )
        logger.info("flowwow order id=%s created crm_id=%s", item["id"], crm_order.pk)
        print(f"flowwow order id={item['id']} created crm_id={crm_order.pk}", flush=True)
    else:
        for name, value in fields.items():
            setattr(crm_order, name, value)
        crm_order.save(update_fields=[*fields, "updated_at"])
        logger.info("flowwow order id=%s updated crm_id=%s", item["id"], crm_order.pk)
        print(f"flowwow order id={item['id']} updated crm_id={crm_order.pk}", flush=True)
    _sync_images(crm_order, item)
    return crm_order


def _crm_fields(item: dict) -> dict:
    start = datetime.fromtimestamp(item["deliveryDateFrom"], tz=_TB)
    end = datetime.fromtimestamp(item["deliveryDateTo"], tz=_TB)
    time_type = item["deliveryTimeType"]
    if time_type == _DELIVERY_TIME_INTERVAL:
        time_start = start.time().replace(second=0, microsecond=0)
        time_end = end.time().replace(second=0, microsecond=0)
        when_ready = False
    elif time_type == _DELIVERY_TIME_ASAP:
        time_start = None
        time_end = None
        when_ready = True
    else:
        time_start = None
        time_end = None
        when_ready = False
    if item["deliveryType"] == _DELIVERY_TYPE_PICKUP:
        fulfillment_type = CrmOrder.FULFILLMENT_PICKUP
    else:
        fulfillment_type = CrmOrder.FULFILLMENT_DELIVERY
    products = item["products"]
    cake_price = sum(
        (Decimal(product["price"]) * product["count"] for product in products),
        Decimal("0.00"),
    )
    return {
        "date": start.date(),
        "time_start": time_start,
        "time_end": time_end,
        "when_ready": when_ready,
        "contact": _contact(item),
        "delivery_address": item["address"],
        "fulfillment_type": fulfillment_type,
        "weight": _weight(products),
        "filling": _filling(products),
        "description": _description(item),
        "internal_description": item["shopAdditionalInfo"] or "",
        "cake_price": cake_price,
        "prepayment": cake_price,
        "is_paid": True,
        "payment_type": CrmOrder.PAYMENT_FLOWWOW,
    }


def _contact(item: dict) -> str:
    person = item["recipient"] if item.get("recipient") is not None else item.get("user")
    return _person_label(person)


def _person_label(person: dict | None) -> str:
    if person is None:
        return ""
    return f"{person.get('name') or ''} {person.get('phone') or ''}".strip()


def _filling(products: list[dict]) -> str:
    values: list[str] = []
    for product in products:
        if product["type"] == _PRODUCT_TYPE_ADDITIONAL:
            continue
        for prop in product.get("selectedProperties") or []:
            title = prop["propertyTitle"].strip().casefold()
            if prop["propertyId"] == _FILLING_PROPERTY_ID or title in _FILLING_PROPERTY_TITLES:
                _append_unique(values, prop["valueTitle"].strip())
    return ", ".join(values) if values else "—"


def _weight(products: list[dict]) -> str:
    values: list[str] = []
    for product in products:
        if product["type"] == _PRODUCT_TYPE_ADDITIONAL:
            continue
        properties = product.get("selectedProperties") or []
        property_weights = [
            prop["valueTitle"].strip()
            for prop in properties
            if prop["propertyTitle"].strip().casefold() in _WEIGHT_PROPERTY_TITLES
        ]
        if property_weights:
            for value in property_weights:
                _append_unique(values, value)
            continue
        for text in (product["name"], product.get("description") or ""):
            match = _WEIGHT_RE.search(text)
            if match is not None:
                _append_unique(values, match.group().strip())
                break
    return ", ".join(values) if values else "—"


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _description(item: dict) -> str:
    lines = [f"Flowwow #{item['id']}"]
    for product in item["products"]:
        line = f"{product['name']} × {product['count']} — {product['price']}"
        props = product.get("selectedProperties") or []
        if props:
            opt_parts = [f"{p['propertyTitle']}: {p['valueTitle']}" for p in props]
            line += f"\n  {', '.join(opt_parts)}"
        lines.append(line)
    message = item.get("message") or ""
    if message:
        lines.append(f"Открытка: {message}")
    user = item.get("user")
    if user:
        lines.append(f"Покупатель: {_person_label(user)}")
    comment = item.get("comment") or ""
    if comment:
        lines.append(comment)
    courier = item.get("courierInfo") or ""
    if courier:
        lines.append(f"Курьеру: {courier}")
    return "\n".join(lines)


def _sync_images(crm_order: CrmOrder, item: dict) -> None:
    urls: list[str] = []
    seen: set[str] = set()
    for product in item["products"]:
        for url in product.get("images") or []:
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)
    existing = {
        image.source_url: image
        for image in crm_order.images.exclude(source_url=None)
    }
    wanted = set(urls)
    for url, image in existing.items():
        if url not in wanted:
            image.delete()
    last = crm_order.images.order_by("-position").first()
    next_position = last.position + 1 if last else 0
    remaining = {
        image.source_url: image
        for image in crm_order.images.exclude(source_url=None)
    }
    for url in urls:
        if url in remaining:
            continue
        name = Path(urlparse(url).path).name
        CrmOrderImage.objects.create(
            order=crm_order,
            image=ContentFile(_download_image(url), name=name),
            position=next_position,
            source_url=url,
        )
        next_position += 1


def _download_image(url: str) -> bytes:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content
