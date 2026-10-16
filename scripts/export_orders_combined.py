import csv
import json
import re
import sqlite3
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
XLSX_PATH = ROOT / "Таблица_заказов_Sweet_Chill.xlsx"
DB_PATH = ROOT / "backend" / "db.sqlite3"
HTML_PATH = ROOT / "orders_telegram.html"
CSV_PATH = ROOT / "orders_combined.csv"
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
TODAY_RE = re.compile(r"на сегодня|заказ(?:ы)?\s+сегодня", re.IGNORECASE)
TOMORROW_RE = re.compile(
    r"на завтра|заказ(?:ы)?\s+на завтра|торт(?:ы)?\s+на завтра",
    re.IGNORECASE,
)
ITEM_SPLIT_RE = re.compile(r"(?m)^[ \t]*\d+[.)][ \t]*(?!\d)")
ITEM_MESSAGE_RE = re.compile(r"^\s*\d+[.)][ \t]*(?!\d)")
NAME_STOP = {
    "дизайн",
    "доставка",
    "самовывоз",
    "адрес",
    "батуми",
    "телефон",
    "номер",
    "заказ",
    "торт",
    "открытку",
}
CRM_CUTOFF = date(2026, 8, 22)
NAMED_PRICE_LIMIT = Decimal("15")
GENERIC_PRICE_LIMIT = Decimal("5")
GENERIC_NAMES = {"флао", "флоу", "сайт", "вотсап", "смм"}
FLOWWOW_RE = re.compile(r"флао|флоу|флау|фоал|flowwow", re.IGNORECASE)
WEBSITE_RE = re.compile(r"(?<![0-9a-zа-яё])сайт(?![0-9a-zа-яё])", re.IGNORECASE)
WHATSAPP_RE = re.compile(r"вотс\w*|воцап\w*|ватсап\w*|вацап\w*|whats?\s*app", re.IGNORECASE)
COLUMNS = [
    "source",
    "excel_sheet",
    "excel_row",
    "crm_id",
    "date",
    "time",
    "client_name",
    "contact",
    "phone",
    "fulfillment",
    "weight",
    "filling",
    "description",
    "cake_price",
    "prepayment",
    "remainder",
    "is_paid",
    "payment_type",
    "is_flowwow",
    "is_website",
    "is_whatsapp",
    "payment_date",
    "status",
    "delivery_address",
    "deleted",
    "note",
]
SHEET_COLUMNS: dict[str, dict[str, int | None]] = {
    "июнь": {
        "note": None,
        "name": 2,
        "phone": 3,
        "channel": None,
        "weight": 4,
        "filling": 5,
        "description": 6,
        "price": 7,
        "prepayment": 8,
        "remainder": 9,
    },
    "июль": {
        "note": 2,
        "name": 3,
        "phone": 4,
        "channel": None,
        "weight": 5,
        "filling": 6,
        "description": 7,
        "price": 8,
        "prepayment": 9,
        "remainder": 10,
    },
    "август": {
        "note": None,
        "name": 2,
        "phone": None,
        "channel": 3,
        "weight": 4,
        "filling": 5,
        "description": 6,
        "price": 7,
        "prepayment": 8,
        "remainder": 9,
    },
    "сентябрь": {
        "note": None,
        "name": 2,
        "phone": None,
        "channel": None,
        "weight": 3,
        "filling": 4,
        "description": 5,
        "price": 6,
        "prepayment": 7,
        "remainder": 8,
    },
}


def format_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def format_phone(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    text = str(value).replace("\u202a", "").replace("\u202c", "").replace("\xa0", " ")
    return text.strip()


def format_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


def parse_money(value) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def format_excel_time(cell) -> str:
    value = cell.value
    if value is None:
        return ""
    if isinstance(value, datetime):
        if cell.number_format == "d-m":
            return f"{value.day}-{value.month}"
        return value.strftime("%H:%M")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, (int, float)):
        return f"{int(value):02d}:00"
    return str(value).strip()


def split_channel(value) -> tuple[str, str, str]:
    if value is None or value == "":
        return "", "", ""
    if isinstance(value, (int, float)):
        return format_phone(value), "", ""
    raw = str(value).strip()
    label = raw.lower().replace("ё", "е").replace(" ", "")
    if label == "доставка":
        return "", "delivery", ""
    if label in {"самовывоз", "с/в"}:
        return "", "pickup", ""
    compact = re.sub(r"[\s+\-()]", "", raw)
    if compact.isdigit():
        return raw, "", ""
    return "", "", raw


def normalize_name(value: str) -> str:
    text = value.lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", "", text)


def is_generic_name(value: str) -> bool:
    normalized = normalize_name(value)
    return normalized == "" or normalized in GENERIC_NAMES


def names_match(excel_name: str, nickname: str, contact: str) -> bool:
    left = normalize_name(excel_name)
    if len(left) < 4:
        return False
    for raw in (nickname, contact):
        right = normalize_name(raw)
        if len(right) < 4:
            continue
        if left in right or right in left:
            return True
    return False


def filling_words(value: str) -> set[str]:
    text = value.lower().replace("ё", "е")
    return {word for word in re.findall(r"[a-zа-я0-9]+", text) if len(word) >= 3}


def expand_filling(text: str) -> str:
    lowered = text.lower().replace("ё", "е")
    lowered = re.sub(r"ф\s*/\s*м", "фисташка малина", lowered)
    return re.sub(r"(?<![a-zа-я0-9])кб(?![a-zа-я0-9])", "красный бархат", lowered)


def filling_tokens(text: str) -> set[str]:
    return {word for word in filling_words(expand_filling(text)) if not word.isdigit()}


def make_date(year: int, month: int, day: int) -> date | None:
    if month < 1 or month > 12:
        return None
    if day < 1 or day > monthrange(year, month)[1]:
        return None
    return date(year, month, day)


def format_kg(value: Decimal) -> str:
    if value == value.to_integral():
        return str(int(value))
    return format(value.normalize(), "f")


def canonical_weight(number: str, unit: str) -> str:
    value = Decimal(number.replace(",", "."))
    if unit.startswith("кг"):
        if value <= 0 or value > 20:
            return ""
        return format_kg(value)
    grams = int(value)
    if grams % 100 != 0 or grams < 500 or grams > 8000:
        return ""
    return str(grams)


def weight_keys(text: str) -> set[str]:
    lowered = text.lower().replace("ё", "е")
    keys = set()
    for match in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(кг|грамм(?:а|ов)?|гр)\b", lowered):
        key = canonical_weight(match.group(1), match.group(2))
        if key:
            keys.add(key)
    if keys:
        return keys
    for match in re.finditer(
        r"(?<!\d)(600|700|800|900|1000|1200|1500|1800|2000|2500|3000)(?!\d)",
        lowered,
    ):
        keys.add(match.group(1))
    if keys:
        return keys
    match = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*", lowered)
    if match is None:
        return set()
    value = Decimal(match.group(1).replace(",", "."))
    if value < 20:
        return {format_kg(value)}
    grams = int(value)
    if grams % 100 == 0 and 500 <= grams <= 8000:
        return {str(grams)}
    return set()


def prices_within(left: Decimal | None, right: Decimal | None, limit: Decimal) -> bool:
    if left is None or right is None:
        return False
    return abs(left - right) <= limit


def format_crm_clock(value: str | None) -> str:
    if not value:
        return ""
    hour, minute, _second = value.split(":")
    return f"{int(hour):02d}:{int(minute):02d}"


def format_crm_time(when_ready: int, time_start: str | None, time_end: str | None) -> str:
    if when_ready:
        return "when ready"
    start = format_crm_clock(time_start)
    end = format_crm_clock(time_end)
    if start and end and start != end:
        return f"{start}-{end}"
    return start


def format_crm_phones(raw: str) -> str:
    numbers = []
    seen = set()
    for item in json.loads(raw):
        number = str(item["value"]).strip()
        if number and number not in seen:
            seen.add(number)
            numbers.append(number)
    return ", ".join(numbers)


def column_text(row, columns: dict[str, int | None], key: str) -> str:
    index = columns[key]
    if index is None:
        return ""
    return format_text(row[index].value)


def read_excel_order(
    sheet: str,
    row_number: int,
    row,
    columns: dict[str, int | None],
    previous_price: Decimal | None,
) -> dict:
    phone = ""
    fulfillment = ""
    note = ""
    channel_index = columns["channel"]
    if channel_index is not None:
        phone, fulfillment, note = split_channel(row[channel_index].value)
    else:
        phone_index = columns["phone"]
        if phone_index is not None:
            phone = format_phone(row[phone_index].value)
        note_index = columns["note"]
        if note_index is not None:
            note = format_text(row[note_index].value)
    order_date = row[0].value
    return {
        "sheet": sheet,
        "row": row_number,
        "date": order_date.date(),
        "time": format_excel_time(row[1]),
        "name": column_text(row, columns, "name"),
        "phone": phone,
        "fulfillment": fulfillment,
        "weight": column_text(row, columns, "weight"),
        "filling": column_text(row, columns, "filling"),
        "description": column_text(row, columns, "description"),
        "price": previous_price
        if isinstance(row[columns["price"]].value, str)
        and row[columns["price"]].value.strip().lower().replace("ё", "е") == "выше"
        else parse_money(row[columns["price"]].value),
        "prepayment": parse_money(row[columns["prepayment"]].value),
        "remainder": parse_money(row[columns["remainder"]].value),
        "note": note,
    }


def load_excel(path: Path) -> list[dict]:
    workbook = openpyxl.load_workbook(path, data_only=True)
    orders = []
    for worksheet in workbook.worksheets:
        columns = SHEET_COLUMNS[worksheet.title.strip().lower()]
        sheet = worksheet.title.strip()
        for row_number, row in enumerate(worksheet.iter_rows(max_col=13), start=1):
            if not isinstance(row[0].value, datetime):
                continue
            previous_price = orders[-1]["price"] if orders and orders[-1]["sheet"] == sheet else None
            orders.append(read_excel_order(sheet, row_number, row, columns, previous_price))
    return orders


def load_crm(path: Path) -> list[dict]:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    cursor = connection.execute(
        """
        SELECT
            id,
            date,
            time_start,
            time_end,
            when_ready,
            contact,
            nickname,
            phones,
            fulfillment_type,
            weight,
            filling,
            description,
            cake_price,
            prepayment,
            is_paid,
            payment_type,
            payment_date,
            status,
            delivery_address,
            deleted
        FROM crm_crmorder
        ORDER BY date, id
        """
    )
    orders = []
    for row in cursor:
        orders.append(
            {
                "id": row["id"],
                "date": date.fromisoformat(row["date"]),
                "time_start": row["time_start"],
                "time_end": row["time_end"],
                "when_ready": row["when_ready"],
                "contact": row["contact"],
                "nickname": row["nickname"],
                "phones": row["phones"],
                "fulfillment": row["fulfillment_type"],
                "weight": row["weight"],
                "filling": row["filling"],
                "description": row["description"],
                "price": Decimal(row["cake_price"]),
                "prepayment": Decimal(row["prepayment"]),
                "is_paid": row["is_paid"],
                "payment_type": row["payment_type"],
                "payment_date": row["payment_date"] or "",
                "status": row["status"],
                "delivery_address": row["delivery_address"],
                "deleted": row["deleted"],
            }
        )
    connection.close()
    return orders


def is_candidate(excel: dict, crm: dict) -> bool:
    if excel["date"] != crm["date"]:
        return False
    if is_generic_name(excel["name"]):
        return prices_within(excel["price"], crm["price"], GENERIC_PRICE_LIMIT) and bool(
            filling_words(excel["filling"]) & filling_words(crm["filling"])
        )
    if not names_match(excel["name"], crm["nickname"], crm["contact"]):
        return False
    if prices_within(excel["price"], crm["price"], NAMED_PRICE_LIMIT):
        return True
    if excel["price"] is None or crm["price"] is None:
        return True
    return bool(filling_words(excel["filling"]) & filling_words(crm["filling"]))


def excel_csv_row(excel: dict) -> dict[str, str]:
    return {
        "source": "excel",
        "excel_sheet": excel["sheet"],
        "excel_row": str(excel["row"]),
        "crm_id": "",
        "date": excel["date"].isoformat(),
        "time": excel["time"],
        "client_name": excel["name"],
        "contact": excel["name"],
        "phone": excel["phone"],
        "fulfillment": excel["fulfillment"],
        "weight": excel["weight"],
        "filling": excel["filling"],
        "description": excel["description"],
        "cake_price": format_decimal(excel["price"]),
        "prepayment": format_decimal(excel["prepayment"]),
        "remainder": format_decimal(excel["remainder"]),
        "is_paid": "",
        "payment_type": "",
        "payment_date": "",
        "status": "",
        "delivery_address": "",
        "deleted": "",
        "note": excel["note"],
    }


def crm_csv_row(crm: dict, excel: dict | None) -> dict[str, str]:
    nickname = crm["nickname"].strip()
    contact = crm["contact"].strip()
    return {
        "source": "both" if excel is not None else "crm",
        "excel_sheet": excel["sheet"] if excel is not None else "",
        "excel_row": str(excel["row"]) if excel is not None else "",
        "crm_id": str(crm["id"]),
        "date": crm["date"].isoformat(),
        "time": format_crm_time(crm["when_ready"], crm["time_start"], crm["time_end"]),
        "client_name": nickname or contact,
        "contact": contact,
        "phone": format_crm_phones(crm["phones"]),
        "fulfillment": crm["fulfillment"],
        "weight": crm["weight"].strip(),
        "filling": crm["filling"].strip(),
        "description": crm["description"].strip(),
        "cake_price": format_decimal(crm["price"]),
        "prepayment": format_decimal(crm["prepayment"]),
        "remainder": format_decimal(crm["price"] - crm["prepayment"]),
        "is_paid": "1" if crm["is_paid"] else "0",
        "payment_type": crm["payment_type"],
        "payment_date": crm["payment_date"],
        "status": crm["status"],
        "delivery_address": crm["delivery_address"].strip(),
        "deleted": "1" if crm["deleted"] else "0",
        "note": "",
    }


class TelegramExportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[dict] = []
        self.current: dict | None = None
        self.capture: str | None = None
        self.buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        class_name = attributes.get("class", "")
        if tag == "div" and class_name.startswith("message default"):
            self.current = {"id": attributes.get("id", ""), "title": "", "text": ""}
            self.messages.append(self.current)
        if self.current is not None and tag == "div" and "date details" in class_name:
            self.capture = "date"
            self.buffer = []
            if attributes.get("title"):
                self.current["title"] = attributes["title"]
        elif self.current is not None and tag == "div" and class_name.strip() == "text":
            self.capture = "text"
            self.buffer = []
        if tag == "br" and self.capture == "text":
            self.buffer.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag != "div" or self.capture is None:
            return
        if self.capture == "text" and self.current is not None:
            self.current["text"] = "".join(self.buffer).strip()
        self.capture = None
        self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.capture == "text":
            self.buffer.append(data)


def posted_date(title: str) -> date | None:
    match = re.match(r"(\d{1,2}) ([A-Za-z]+) (\d{4})", title.strip())
    if match is None:
        return None
    return make_date(int(match.group(3)), MONTHS[match.group(2).lower()], int(match.group(1)))


def clean_telegram_text(text: str) -> str:
    cleaned = text.replace("\u202a", "").replace("\u202c", "").replace("\u202b", "")
    return cleaned.replace("\xa0", " ").strip()


def load_telegram(path: Path) -> list[dict]:
    parser = TelegramExportParser()
    parser.feed(path.read_text(encoding="utf-8"))
    messages = []
    for message in parser.messages:
        messages.append(
            {
                "id": message["id"],
                "posted": posted_date(message["title"]),
                "text": clean_telegram_text(message["text"]),
            }
        )
    return messages


def resolve_delivery(text: str, posted: date, previous: tuple[date, date] | None) -> date | None:
    match = re.match(r"^\s*(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?", text)
    if match is not None:
        year = posted.year
        if match.group(3):
            raw_year = int(match.group(3))
            year = raw_year + 2000 if raw_year < 100 else raw_year
        return make_date(year, int(match.group(2)), int(match.group(1)))
    if TODAY_RE.search(text):
        return posted
    if TOMORROW_RE.search(text):
        return posted + timedelta(days=1)
    if previous is None or previous[0] != posted:
        return None
    if ITEM_MESSAGE_RE.match(text) or weight_keys(text):
        return previous[1]
    return None


def split_items(text: str) -> list[str]:
    matches = list(ITEM_SPLIT_RE.finditer(text))
    if not matches:
        return [text]
    parts = []
    preamble = text[: matches[0].start()].strip()
    if weight_keys(preamble):
        parts.append(preamble)
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        part = text[match.end() : end].strip()
        if part:
            parts.append(part)
    return parts


def filling_line(text: str) -> str:
    fallback = ""
    for line in text.splitlines():
        stripped = line.strip(" -:\t")
        if not stripped or re.match(
            r"^(всем|заказ|на завтра|на сегодня|торты на|торт на|\d{1,2}[./]\d{1,2}\b)",
            stripped,
            re.IGNORECASE,
        ):
            continue
        if not fallback:
            fallback = stripped
        if weight_keys(stripped):
            return stripped
    return fallback


def phones_from_text(text: str) -> str:
    found = []
    pattern = re.compile(
        r"(?<!\d)(?:\+\d[\d\s\-()]{7,}\d|\b\d{9,15}\b|\b\d{3}[\s\-]\d{2,3}[\s\-]\d{2,4}\b)"
    )
    for match in pattern.finditer(text):
        raw = re.sub(r"\s+", " ", match.group(0)).strip()
        digits = re.sub(r"\D", "", raw)
        if len(digits) < 9 or len(digits) > 15 or raw in found:
            continue
        found.append(raw)
    return ", ".join(found)


def address_from_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if re.search(r"адрес", line, re.IGNORECASE) is None:
            continue
        rest = re.sub(r"^.*адрес\w*\s*[:\-—]*\s*", "", line, flags=re.IGNORECASE).strip(" -:—")
        chunks = [rest] if rest else []
        for follow in lines[index + 1 :]:
            if re.match(r"^(дизайн|доставк|самовывоз|телефон|номер)\b", follow, re.IGNORECASE):
                break
            if re.match(r"^[сc]\s+\d{1,2}:\d{2}", follow, re.IGNORECASE):
                break
            if re.match(r"^(в|к)\s+\d", follow, re.IGNORECASE):
                break
            if phones_from_text(follow):
                break
            chunks.append(follow)
        if chunks:
            return " ".join(chunks)
    for line in lines:
        if re.search(r"https?://", line) and re.search(r"maps|yandex|goo\.gl|google", line, re.IGNORECASE):
            return line
    for line in lines:
        if re.search(r"улиц|ул\.|переул|батуми|пирсмани|агмашенебели|качинск", line, re.IGNORECASE):
            return line
    return ""


def fulfillment_from_text(text: str) -> str:
    lowered = text.lower().replace("ё", "е")
    pickup_at = lowered.find("самовывоз")
    delivery_at = lowered.find("достав")
    if pickup_at >= 0 and (delivery_at < 0 or pickup_at < delivery_at):
        return "pickup"
    if delivery_at >= 0:
        return "delivery"
    return ""


def time_from_text(text: str) -> str:
    lowered = text.lower().replace("ё", "е")
    match = re.search(r"с\s+(\d{1,2}:\d{2})\s+до\s+(\d{1,2}:\d{2})", lowered)
    if match is not None:
        return f"{match.group(1)}-{match.group(2)}"
    match = re.search(r"(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})", lowered)
    if match is not None:
        return f"{match.group(1)}-{match.group(2)}"
    match = re.search(r"(?<!\d)(\d{1,2})\s*[-–—]\s*(\d{1,2})(?!\d)", lowered)
    if match is not None and int(match.group(1)) <= 23 and int(match.group(2)) <= 23:
        return f"{int(match.group(1)):02d}:00-{int(match.group(2)):02d}:00"
    match = re.search(r"(?:в|к|на)\s+(\d{1,2}:\d{2})", lowered)
    if match is not None:
        return match.group(1)
    match = re.search(r"(?:в|к|на)\s+(\d{1,2})(?!\d)", lowered)
    if match is not None and int(match.group(1)) <= 23:
        return f"{int(match.group(1)):02d}:00"
    match = re.search(r"\b(\d{1,2}:\d{2})\b", lowered)
    if match is not None:
        return match.group(1)
    return ""


def design_text(text: str) -> str:
    match = re.search(r"дизайн\s*[:\-—]?\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if match is None:
        return ""
    lines = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if re.match(
            r"^(адрес|по адрес|доставк|самовывоз|телефон|номер|\+?\d[\d\s\-()]{8,})",
            stripped,
            re.IGNORECASE,
        ):
            break
        if stripped:
            lines.append(stripped)
    return " ".join(lines)


def client_name_from_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        if not re.search(r"\d{6,}", line):
            continue
        inline = re.search(
            r"\d{6,}(?:\s*[,/]\s*|\s+)([A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё\-]{2,30})$",
            line,
        )
        if inline is not None and inline.group(1).lower() not in NAME_STOP:
            return inline.group(1)
        if index + 1 < len(lines):
            nxt = lines[index + 1]
            if re.fullmatch(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё\-]{2,30}", nxt) and nxt.lower() not in NAME_STOP:
                return nxt
    return ""


def build_card(message_id: str, delivery: date, text: str) -> dict:
    return {
        "id": message_id,
        "date": delivery,
        "weights": weight_keys(text),
        "filling": filling_line(text),
        "phone": phones_from_text(text),
        "address": address_from_text(text),
        "fulfillment": fulfillment_from_text(text),
        "time": time_from_text(text),
        "design": design_text(text),
        "client_name": client_name_from_text(text),
    }


def cards_from_messages(messages: list[dict]) -> list[dict]:
    cards = []
    previous: tuple[date, date] | None = None
    for message in messages:
        posted = message["posted"]
        text = message["text"]
        if posted is None or not text:
            continue
        if re.search(r"перенос", text, re.IGNORECASE):
            continue
        if re.search(r"заказ номер\s+\d+", text, re.IGNORECASE):
            continue
        delivery = resolve_delivery(text, posted, previous)
        if delivery is None:
            continue
        emitted = False
        for part in split_items(text):
            if not weight_keys(part):
                continue
            cards.append(build_card(message["id"], delivery, part))
            emitted = True
        if emitted:
            previous = (posted, delivery)
    return cards


def telegram_match(card: dict, row: dict[str, str]) -> bool:
    if row["date"] != card["date"].isoformat():
        return False
    if not (card["weights"] & weight_keys(row["weight"])):
        return False
    return bool(filling_tokens(card["filling"]) & filling_tokens(row["filling"]))


def append_message_id(row: dict[str, str], message_id: str) -> None:
    if message_id and message_id in row["note"].split():
        return
    if row["note"]:
        row["note"] = f"{row['note']} {message_id}"
    else:
        row["note"] = message_id


def apply_card(row: dict[str, str], card: dict) -> bool:
    changed = False
    updates = {
        "phone": card["phone"],
        "delivery_address": card["address"],
        "fulfillment": card["fulfillment"],
        "time": card["time"],
        "description": card["design"],
        "client_name": card["client_name"],
    }
    for key, value in updates.items():
        if row[key] or not value:
            continue
        row[key] = value
        changed = True
    if changed:
        append_message_id(row, card["id"])
    return changed


def apply_crm_number_notes(rows: list[dict[str, str]], messages: list[dict]) -> None:
    for message in messages:
        match = re.search(r"заказ номер\s+(\d+)", message["text"], re.IGNORECASE)
        if match is None:
            continue
        crm_id = match.group(1)
        for row in rows:
            if row["crm_id"] == crm_id and not row["note"]:
                row["note"] = f"{message['id']}\n{message['text']}"


def enrich_rows(rows: list[dict[str, str]], messages: list[dict]) -> None:
    apply_crm_number_notes(rows, messages)
    used: set[int] = set()
    for card in cards_from_messages(messages):
        candidates = [index for index, row in enumerate(rows) if telegram_match(card, row)]
        if len(candidates) != 1 or candidates[0] in used:
            continue
        if apply_card(rows[candidates[0]], card):
            used.add(candidates[0])


def combine(excel_orders: list[dict], crm_orders: list[dict]) -> list[dict[str, str]]:
    used_crm_ids = set()
    rows = []
    for excel in excel_orders:
        if excel["date"] < CRM_CUTOFF:
            rows.append(excel_csv_row(excel))
            continue
        candidates = [crm for crm in crm_orders if is_candidate(excel, crm)]
        if len(candidates) == 1 and candidates[0]["id"] not in used_crm_ids:
            used_crm_ids.add(candidates[0]["id"])
            rows.append(crm_csv_row(candidates[0], excel))
            continue
        rows.append(excel_csv_row(excel))
    for crm in crm_orders:
        if crm["id"] not in used_crm_ids:
            rows.append(crm_csv_row(crm, None))
    return rows


def apply_channel_flags(row: dict[str, str]) -> None:
    text = "\n".join((row["client_name"], row["contact"], row["description"], row["note"]))
    row["is_flowwow"] = "1" if row["payment_type"] == "flowwow" or FLOWWOW_RE.search(text) else "0"
    row["is_website"] = "1" if row["payment_type"] == "online" or WEBSITE_RE.search(text) else "0"
    row["is_whatsapp"] = "1" if WHATSAPP_RE.search(text) else "0"


def sort_key(row: dict[str, str]) -> tuple[str, str, str, int, int]:
    return (
        row["date"],
        row["time"],
        row["excel_sheet"],
        int(row["excel_row"]) if row["excel_row"] else 0,
        int(row["crm_id"]) if row["crm_id"] else 0,
    )


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    rows.sort(key=sort_key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = combine(load_excel(XLSX_PATH), load_crm(DB_PATH))
    enrich_rows(rows, load_telegram(HTML_PATH))
    for row in rows:
        apply_channel_flags(row)
    write_csv(CSV_PATH, rows)


if __name__ == "__main__":
    main()
