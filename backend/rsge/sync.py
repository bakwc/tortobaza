from datetime import date, datetime, timedelta
from decimal import Decimal
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from rsge.client import fetch_buyer_waybills, fetch_waybill_goods
from rsge.models import Waybill, WaybillGood, WaybillSync

TB = ZoneInfo("Asia/Tbilisi")
RECENT_DAYS = 3
MAX_DAYS = 30
CHUNK_DAYS = 3


def window_start(now: datetime, last_synced_at: datetime | None) -> date:
    today = now.astimezone(TB).date()
    earliest = today - timedelta(days=MAX_DAYS)
    if last_synced_at is None:
        return earliest
    if now - last_synced_at < timedelta(days=RECENT_DAYS):
        return today - timedelta(days=RECENT_DAYS)
    last_date = last_synced_at.astimezone(TB).date()
    if last_date < earliest:
        return earliest
    return last_date


def chunk_bounds(start: date, end: date) -> list[tuple[str, str]]:
    bounds = []
    cursor = start
    while cursor <= end:
        chunk_last = cursor + timedelta(days=CHUNK_DAYS - 1)
        if chunk_last > end:
            chunk_last = end
        create_date_s = cursor.isoformat() + "T00:00:00"
        create_date_e = (chunk_last + timedelta(days=1)).isoformat() + "T00:00:00"
        bounds.append((create_date_s, create_date_e))
        cursor = chunk_last + timedelta(days=1)
    return bounds


def child_text(element: ET.Element, tag: str) -> str | None:
    child = element.find(tag)
    if child is None or child.text is None:
        return None
    text = child.text.strip()
    if not text:
        return None
    return text


def require_child(element: ET.Element, tag: str) -> str:
    value = child_text(element, tag)
    if value is None:
        raise RuntimeError(
            f"RS.ge element missing {tag}\n" + ET.tostring(element, encoding="unicode")
        )
    return value


def blank(element: ET.Element, tag: str) -> str:
    value = child_text(element, tag)
    if value is None:
        return ""
    return value


def optional_int(element: ET.Element, tag: str) -> int | None:
    value = child_text(element, tag)
    if value is None:
        return None
    return int(value)


def parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        return parsed
    return parsed.replace(tzinfo=TB)


def optional_dt(element: ET.Element, tag: str) -> datetime | None:
    value = child_text(element, tag)
    if value is None:
        return None
    return parse_dt(value)


def good_from(waybill: Waybill, element: ET.Element) -> WaybillGood:
    quantity_ext = child_text(element, "QUANTITY_EXT")
    return WaybillGood(
        waybill=waybill,
        rs_id=int(require_child(element, "ID")),
        name=require_child(element, "W_NAME"),
        unit_id=int(require_child(element, "UNIT_ID")),
        unit_txt=blank(element, "UNIT_TXT"),
        quantity=Decimal(require_child(element, "QUANTITY")),
        price=Decimal(require_child(element, "PRICE")),
        amount=Decimal(require_child(element, "AMOUNT")),
        bar_code=blank(element, "BAR_CODE"),
        a_id=int(require_child(element, "A_ID")),
        vat_type=int(require_child(element, "VAT_TYPE")),
        quantity_ext=None if quantity_ext is None else Decimal(quantity_ext),
        status=int(require_child(element, "STATUS")),
        quantity_f=Decimal(require_child(element, "QUANTITY_F")),
    )


def save_waybill(su: str, sp: str, element: ET.Element) -> None:
    rs_id = int(require_child(element, "ID"))
    if Waybill.objects.filter(rs_id=rs_id).exists():
        return
    goods = fetch_waybill_goods(su, sp, str(rs_id))
    with transaction.atomic():
        waybill = Waybill.objects.create(
            rs_id=rs_id,
            waybill_number=require_child(element, "WAYBILL_NUMBER"),
            type=int(require_child(element, "TYPE")),
            status=int(require_child(element, "STATUS")),
            create_date=parse_dt(require_child(element, "CREATE_DATE")),
            activate_date=parse_dt(require_child(element, "ACTIVATE_DATE")),
            begin_date=parse_dt(require_child(element, "BEGIN_DATE")),
            delivery_date=optional_dt(element, "DELIVERY_DATE"),
            close_date=optional_dt(element, "CLOSE_DATE"),
            buyer_tin=require_child(element, "BUYER_TIN"),
            buyer_name=require_child(element, "BUYER_NAME"),
            seller_tin=require_child(element, "SELLER_TIN"),
            seller_name=require_child(element, "SELLER_NAME"),
            start_address=blank(element, "START_ADDRESS"),
            end_address=blank(element, "END_ADDRESS"),
            driver_tin=blank(element, "DRIVER_TIN"),
            driver_name=blank(element, "DRIVER_NAME"),
            car_number=blank(element, "CAR_NUMBER"),
            reception_info=blank(element, "RECEPTION_INFO"),
            waybill_comment=blank(element, "WAYBILL_COMMENT"),
            transport_coast=Decimal(require_child(element, "TRANSPORT_COAST")),
            full_amount=Decimal(require_child(element, "FULL_AMOUNT")),
            s_user_id=int(require_child(element, "S_USER_ID")),
            par_id=optional_int(element, "PAR_ID"),
            invoice_id=optional_int(element, "INVOICE_ID"),
            is_confirmed=int(require_child(element, "IS_CONFIRMED")),
            is_corrected=int(require_child(element, "IS_CORRECTED")),
            seller_st=int(require_child(element, "SELLER_ST")),
            is_med=int(require_child(element, "IS_MED")),
        )
        WaybillGood.objects.bulk_create([good_from(waybill, good) for good in goods])


def save_new_waybills(su: str, sp: str, result: ET.Element) -> None:
    for element in result.iter("WAYBILL"):
        save_waybill(su, sp, element)


def stored_synced_at() -> datetime | None:
    state = WaybillSync.objects.order_by("pk").first()
    if state is None:
        return None
    return state.synced_at


def mark_synced(now: datetime) -> None:
    state = WaybillSync.objects.order_by("pk").first()
    if state is None:
        WaybillSync.objects.create(synced_at=now)
        return
    state.synced_at = now
    state.save(update_fields=["synced_at"])


def sync_waybills() -> None:
    su = settings.RS_SU
    sp = settings.RS_SP
    if su == "" or sp == "":
        raise RuntimeError("RS_SU and RS_SP are required")
    now = timezone.now()
    start = window_start(now, stored_synced_at())
    end = now.astimezone(TB).date()
    for create_date_s, create_date_e in chunk_bounds(start, end):
        result = fetch_buyer_waybills(su, sp, create_date_s, create_date_e)
        save_new_waybills(su, sp, result)
    mark_synced(now)
