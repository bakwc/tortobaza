import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from crm.models import FlowwowProduct

logger = logging.getLogger(__name__)

_PRODUCTS_URL = "https://apis.flowwow.com/apiseller/products"
_PAGE_LIMIT = 1000
_VOLUME_MEASURE_GRAMS = 2
_CATALOG_MAX_AGE = timedelta(hours=24)


def sync_flowwow_catalog() -> None:
    rows = _fetch_catalog()
    synced_at = timezone.now()
    for raw in rows:
        _upsert_product(raw, synced_at)


def sync_flowwow_catalog_if_stale() -> None:
    cutoff = timezone.now() - _CATALOG_MAX_AGE
    if FlowwowProduct.objects.filter(synced_at__gte=cutoff).exists():
        return
    sync_flowwow_catalog()


def _fetch_catalog() -> list[dict]:
    shop_id = int(settings.FLOWWOW_SHOP_ID.strip('"'))
    token = settings.FLOWWOW_API_TOKEN.strip('"')
    page = 0
    fetched = 0
    rows: list[dict] = []
    while True:
        response = requests.post(
            _PRODUCTS_URL,
            params={"shopId": shop_id},
            json={"extended": True, "limit": _PAGE_LIMIT, "page": page},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "*/*",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        total = payload["total"]
        items = payload["items"]
        rows.extend(items)
        fetched += len(items)
        if fetched >= total:
            return rows
        if not items:
            raise ValueError("flowwow catalog page empty")
        page += 1


def _upsert_product(raw: dict, synced_at) -> None:
    properties = raw["properties"]
    volume_grams = None
    fillings: list[str] = []
    if properties is not None:
        volume_grams = _volume_grams(raw["productId"], properties.get("volume"))
        filling = properties.get("filling")
        if filling is not None:
            fillings = list(filling)
    FlowwowProduct.objects.update_or_create(
        product_id=raw["productId"],
        defaults={
            "offer_id": raw["offerId"] or "",
            "name": raw["name"],
            "type": raw["type"],
            "category_id": raw["categoryId"],
            "sub_category_id": raw["subCategoryId"],
            "volume_grams": volume_grams,
            "fillings": fillings,
            "is_active": raw["isActive"],
            "is_archived": raw["isArchived"],
            "synced_at": synced_at,
        },
    )


def _volume_grams(product_id: int, volume: dict | None) -> int | None:
    if volume is None:
        return None
    if volume["measure"] != _VOLUME_MEASURE_GRAMS:
        logger.error(
            "flowwow product volume measure product_id=%s measure=%s val=%s",
            product_id,
            volume["measure"],
            volume["val"],
        )
        return None
    return int(volume["val"])
