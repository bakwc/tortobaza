import calendar
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from rsge.client import (
    call_chek,
    call_get_un_id,
    fetch_buyer_invoices,
    fetch_buyer_waybills,
    fetch_invoice_lines,
    fetch_waybill_goods,
)
from rsge.models import Invoice, InvoiceLine, InvoiceSync, Waybill, WaybillGood, WaybillSync

TB = ZoneInfo("Asia/Tbilisi")
RECENT_DAYS = 3
MAX_MONTHS = 10
CHUNK_DAYS = 3


def months_ago(day: date, months: int) -> date:
    month_index = day.year * 12 + (day.month - 1) - months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def window_start(now: datetime, last_synced_at: datetime | None) -> date:
    today = now.astimezone(TB).date()
    earliest = months_ago(today, MAX_MONTHS)
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


def optional_decimal(element: ET.Element, tag: str) -> Decimal | None:
    value = child_text(element, tag)
    if value is None:
        return None
    return Decimal(value)


def line_from(invoice: Invoice, element: ET.Element) -> InvoiceLine:
    return InvoiceLine(
        invoice=invoice,
        rs_id=int(require_child(element, "ID")),
        goods=require_child(element, "GOODS"),
        unit=require_child(element, "G_UNIT"),
        quantity=Decimal(require_child(element, "G_NUMBER")),
        full_amount=Decimal(require_child(element, "FULL_AMOUNT")),
        vat_amount=Decimal(require_child(element, "DRG_AMOUNT")),
        excise_amount=optional_decimal(element, "AQCIZI_AMOUNT"),
        excise_id=int(require_child(element, "AKCIS_ID")),
        waybill_id=optional_int(element, "WAYBILL_ID"),
        vat_type=int(require_child(element, "VAT_TYPE")),
    )


def save_invoice(su: str, sp: str, user_id: str, element: ET.Element) -> None:
    rs_id = int(require_child(element, "ID"))
    if Invoice.objects.filter(rs_id=rs_id).exists():
        return
    lines = fetch_invoice_lines(su, sp, user_id, str(rs_id))
    with transaction.atomic():
        invoice = Invoice.objects.create(
            rs_id=rs_id,
            seller_un_id=int(require_child(element, "SELLER_UN_ID")),
            seq_num_b=optional_int(element, "SEQ_NUM_B"),
            status=int(require_child(element, "STATUS")),
            was_ref=int(require_child(element, "WAS_REF")),
            series=require_child(element, "F_SERIES"),
            number=require_child(element, "F_NUMBER"),
            reg_dt=parse_dt(require_child(element, "REG_DT")),
            operation_dt=parse_dt(require_child(element, "OPERATION_DT")),
            s_user_id=int(require_child(element, "S_USER_ID")),
            b_s_user_id=int(require_child(element, "B_S_USER_ID")),
            doc_mos_nom=blank(element, "DOC_MOS_NOM_B"),
            seller_tin=require_child(element, "SA_IDENT_NO"),
            org_name=require_child(element, "ORG_NAME"),
            notes=blank(element, "NOTES"),
            amount=Decimal(require_child(element, "TANXA")),
            vat=Decimal(require_child(element, "VAT")),
            k_id=int(require_child(element, "K_ID")),
            agree_date=optional_dt(element, "AGREE_DATE"),
            agree_s_user_id=optional_int(element, "AGREE_S_USER_ID"),
            ref_date=optional_dt(element, "REF_DATE"),
            ref_s_user_id=optional_int(element, "REF_S_USER_ID"),
            note=blank(element, "NOTE"),
        )
        InvoiceLine.objects.bulk_create([line_from(invoice, line) for line in lines])


def save_new_invoices(su: str, sp: str, user_id: str, rows: list[ET.Element]) -> None:
    for element in rows:
        save_invoice(su, sp, user_id, element)


def stored_invoice_synced_at() -> datetime | None:
    state = InvoiceSync.objects.order_by("pk").first()
    if state is None:
        return None
    return state.synced_at


def mark_invoices_synced(now: datetime) -> None:
    state = InvoiceSync.objects.order_by("pk").first()
    if state is None:
        InvoiceSync.objects.create(synced_at=now)
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
    for index, (create_date_s, create_date_e) in enumerate(chunk_bounds(start, end)):
        if index:
            time.sleep(1)
        result = fetch_buyer_waybills(su, sp, create_date_s, create_date_e)
        save_new_waybills(su, sp, result)
    mark_synced(now)


def sync_invoices() -> None:
    su = settings.RS_SU
    sp = settings.RS_SP
    if su == "" or sp == "":
        raise RuntimeError("RS_SU and RS_SP are required")
    now = timezone.now()
    start = window_start(now, stored_invoice_synced_at())
    end = now.astimezone(TB).date()
    user_id = call_chek(su, sp)
    un_id = call_get_un_id(su, sp, user_id)
    for index, (s_dt, e_dt) in enumerate(chunk_bounds(start, end)):
        if index:
            time.sleep(1)
        rows = fetch_buyer_invoices(su, sp, user_id, un_id, s_dt, e_dt)
        save_new_invoices(su, sp, user_id, rows)
    mark_invoices_synced(now)
