import json
import re
import secrets
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from django.db import migrations

from crm.phone import phones_from_fields

LEGACY_ID_START = 1_000_000
CRM_ORDER_TABLE = "crm_crmorder"
DATA_PATH = Path(__file__).with_name("legacy_crm_orders.json")
TBILISI = ZoneInfo("Asia/Tbilisi")
FULFILLMENT_PHONE_LABELS = frozenset({"самовывоз", "доставка"})
KEPT_PHONE_TEXT = "Тг Даши"
CLOCK_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
CLOCK_RANGE_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*[-–—]\s*(\d{1,2}):(\d{2})$")
HOUR_RANGE_RE = re.compile(r"^(\d{1,2})\s*[-–—]\s*(\d{1,2})$")
APPROX_HOUR_RE = re.compile(r"^примерно\s+(\d{1,2})$", re.IGNORECASE)
PREFERRED_HOUR_RE = re.compile(r"^(\d{1,2})\s+желательно$", re.IGNORECASE)


def load_legacy_rows() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def clock(hour: str, minute: str) -> time:
    return time(int(hour), int(minute))


def parse_legacy_time(raw: str) -> tuple[time | None, time | None, str]:
    text = raw.strip()
    if text == "":
        return None, None, ""
    match = CLOCK_RANGE_RE.fullmatch(text)
    if match is not None:
        return clock(match.group(1), match.group(2)), clock(match.group(3), match.group(4)), ""
    match = CLOCK_RE.fullmatch(text)
    if match is not None:
        return clock(match.group(1), match.group(2)), None, ""
    match = HOUR_RANGE_RE.fullmatch(text)
    if match is not None:
        return time(int(match.group(1)), 0), time(int(match.group(2)), 0), ""
    match = APPROX_HOUR_RE.fullmatch(text)
    if match is not None:
        return time(int(match.group(1)), 0), None, ""
    match = PREFERRED_HOUR_RE.fullmatch(text)
    if match is not None:
        return time(int(match.group(1)), 0), None, ""
    return None, None, text


def legacy_contact(name: str, phone: str) -> tuple[str, str]:
    nickname = name.strip()
    phone_text = phone.strip()
    if phone_text.lower().replace("ё", "е") in FULFILLMENT_PHONE_LABELS:
        phone_text = ""
    if phone_text and (phones_from_fields(phone_text, "") or phone_text == KEPT_PHONE_TEXT):
        contact = phone_text
    else:
        contact = nickname
    if contact == "":
        contact = "—"
    return contact, nickname


def legacy_payment_type(is_flowwow: str, is_website: str) -> str:
    if is_flowwow == "1":
        return "flowwow"
    if is_website == "1":
        return "online"
    return "unknown"


def legacy_fulfillment(value: str) -> str:
    if value == "":
        return "delivery"
    return value


def legacy_money(value: str) -> Decimal:
    if value == "":
        return Decimal("0")
    return Decimal(value)


def legacy_weight_description(weight: str, description: str) -> tuple[str, str]:
    if len(weight) <= 50:
        return weight, description
    if description == "":
        return "", weight
    return "", f"{description}\n{weight}"


def legacy_internal_description(sheet: str, row_number: int, unparsed_time: str, note: str) -> str:
    lines = [f"excel:{sheet}:{row_number}"]
    if unparsed_time:
        lines.append(f"time:{unparsed_time}")
    if note:
        lines.append(f"note:{note}")
    return "\n".join(lines)


def legacy_created_at(order_date: date) -> datetime:
    return datetime.combine(order_date, time.min, tzinfo=TBILISI)


def reset_crm_order_sequence(schema_editor) -> None:
    connection = schema_editor.connection
    if connection.vendor != "sqlite":
        raise RuntimeError(connection.vendor)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT MAX(id) FROM crm_crmorder WHERE id < %s",
            [LEGACY_ID_START],
        )
        max_id = cursor.fetchone()[0]
        if max_id is None:
            max_id = 0
        cursor.execute(
            "SELECT 1 FROM sqlite_sequence WHERE name = %s",
            [CRM_ORDER_TABLE],
        )
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO sqlite_sequence (name, seq) VALUES (%s, %s)",
                [CRM_ORDER_TABLE, max_id],
            )
        else:
            cursor.execute(
                "UPDATE sqlite_sequence SET seq = %s WHERE name = %s",
                [max_id, CRM_ORDER_TABLE],
            )


def import_legacy_crm_orders(apps, schema_editor) -> None:
    CrmOrder = apps.get_model("crm", "CrmOrder")
    if CrmOrder.objects.filter(pk__gte=LEGACY_ID_START).exists():
        raise RuntimeError("crm order id >= 1000000 already exists")
    orders = []
    created_ats = []
    for offset, row in enumerate(load_legacy_rows()):
        order_id = LEGACY_ID_START + offset
        order_date = date.fromisoformat(row["date"])
        time_start, time_end, unparsed_time = parse_legacy_time(row["time"])
        contact, nickname = legacy_contact(row["name"], row["phone"])
        weight, description = legacy_weight_description(row["weight"], row["description"])
        created_at = legacy_created_at(order_date)
        orders.append(
            CrmOrder(
                id=order_id,
                date=order_date,
                time_start=time_start,
                time_end=time_end,
                when_ready=False,
                contact=contact,
                is_gift=False,
                nickname=nickname,
                phones=phones_from_fields(contact, nickname),
                delivery_address="",
                fulfillment_type=legacy_fulfillment(row["fulfillment"]),
                status="delivered",
                weight=weight,
                filling=row["filling"],
                description=description,
                internal_description=legacy_internal_description(
                    row["sheet"],
                    row["row"],
                    unparsed_time,
                    row["note"],
                ),
                cake_price=legacy_money(row["cake_price"]),
                delivery_price=Decimal("0"),
                prepayment=legacy_money(row["prepayment"]),
                is_paid=True,
                payment_type=legacy_payment_type(row["is_flowwow"], row["is_website"]),
                payment_date=order_date,
                deleted=False,
                client_token=secrets.token_hex(32),
                telegram_media_ids=[],
                telegram_payload_hash="",
                telegram_posted_when_ready=False,
                telegram_posted_delivery_address="",
                flowwow_synced_description="",
                flowwow_synced_internal_description="",
            )
        )
        created_ats.append((order_id, created_at))
    CrmOrder.objects.bulk_create(orders)
    for order_id, created_at in created_ats:
        CrmOrder.objects.filter(pk=order_id).update(created_at=created_at, updated_at=created_at)
    reset_crm_order_sequence(schema_editor)


def delete_legacy_crm_orders(apps, schema_editor) -> None:
    CrmOrder = apps.get_model("crm", "CrmOrder")
    CrmOrder.objects.filter(pk__gte=LEGACY_ID_START).delete()
    reset_crm_order_sequence(schema_editor)


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0063_rsge_document_links"),
    ]

    operations = [
        migrations.RunPython(import_legacy_crm_orders, delete_legacy_crm_orders),
    ]
