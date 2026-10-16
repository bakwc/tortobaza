import csv
import html
import re
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "orders_combined.csv"
HTML_PATH = ROOT / "orders_analytics.html"
GENERIC_NAMES = {"флао", "флоу", "сайт", "вотсап", "смм", "инст"}
DISTINCTIVE_LENGTH = 10
TOP_LIMIT = 20
FILLING_LIMIT = 10
GAP_BINS = (
    (0, 0, "0"),
    (1, 7, "1–7"),
    (8, 14, "8–14"),
    (15, 30, "15–30"),
    (31, 60, "31–60"),
    (61, 90, "61–90"),
    (91, 100000, "91+"),
)
MONTH_NAMES = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь",
}
SHORT_MONTHS = {
    1: "янв",
    2: "фев",
    3: "мар",
    4: "апр",
    5: "май",
    6: "июн",
    7: "июл",
    8: "авг",
    9: "сен",
    10: "окт",
    11: "ноя",
    12: "дек",
}
PAYMENT_LABELS = {
    "": "нет данных",
    "unknown": "неизвестно",
    "tbc": "TBC",
    "cash": "наличные",
    "flowwow": "Flowwow",
    "bog": "BOG",
    "terminal": "терминал",
    "online": "онлайн",
    "crypto": "крипто",
    "paypal": "PayPal",
    "tbank": "Т-Банк",
}
FULFILLMENT_LABELS = {
    "": "не указано",
    "delivery": "доставка",
    "pickup": "самовывоз",
}
COLOR_NEW = "#3f6b58"
COLOR_RETURN = "#8f3d4b"
COLOR_WHATSAPP = "#3d6f8f"
COLOR_UNKNOWN = "#cfc3b4"
COLOR_INK = "#1f1a17"
COLOR_MUTED = "#6f655e"
COLOR_LINE = "#efe8df"

CSS = """
:root {
  color-scheme: light;
  --bg: #f3efe8;
  --paper: #fffdf9;
  --ink: #1f1a17;
  --muted: #6f655e;
  --line: #e7dfd4;
  --berry: #8f3d4b;
  --moss: #3f6b58;
  --sand: #cfc3b4;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background:
    radial-gradient(900px 420px at 0% -10%, #efe2d2 0%, transparent 55%),
    var(--bg);
  color: var(--ink);
  font: 16px/1.45 "Avenir Next", "Segoe UI", sans-serif;
}
main {
  max-width: 1120px;
  margin: 0 auto;
  padding: 36px 20px 72px;
}
.hero { padding: 8px 4px 4px; }
.eyebrow {
  margin: 0 0 12px;
  color: var(--berry);
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}
h1, h2, h3 {
  font-family: "Iowan Old Style", Palatino, Georgia, serif;
  font-weight: 500;
  letter-spacing: -0.03em;
}
h1 {
  margin: 0 0 16px;
  font-size: 56px;
  line-height: 0.95;
}
h2 { margin: 0 0 8px; font-size: 32px; }
h3 { margin: 0 0 12px; font-size: 22px; }
.lede, .note, .footer { color: #3f3834; }
.lede { max-width: 72ch; margin: 0; }
.note { margin: 0 0 18px; color: var(--muted); font-size: 14px; }
.footer { margin: 22px 4px 0; color: var(--muted); font-size: 13px; }
.kpis {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin: 28px 0 8px;
}
.kpi, section {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 18px;
}
.kpi { padding: 18px 20px 16px; }
section { margin-top: 16px; padding: 26px 26px 22px; }
.label {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.value {
  margin: 8px 0 0;
  font-family: "Iowan Old Style", Palatino, Georgia, serif;
  font-size: clamp(26px, 3vw, 34px);
  letter-spacing: -0.03em;
  line-height: 1.05;
}
.hint { margin: 8px 0 0; color: var(--muted); font-size: 14px; }
.legend { display: flex; flex-wrap: wrap; gap: 14px; margin: 8px 0 14px; }
.legend-item { display: inline-flex; align-items: center; gap: 8px; color: var(--muted); font-size: 13px; }
.legend-item i { width: 10px; height: 10px; border-radius: 99px; display: inline-block; }
svg { width: 100%; height: auto; display: block; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th {
  text-align: left;
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
td, th { padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
table.cohort { border-collapse: separate; border-spacing: 6px 8px; }
table.cohort th, table.cohort td { border: 0; padding: 0 4px; }
table.cohort th[scope="row"] { text-align: left; text-transform: none; letter-spacing: 0; font-size: 14px; color: var(--ink); font-weight: 600; min-width: 140px; }
table.cohort th[scope="row"] small { display: block; color: var(--muted); font-weight: 500; font-size: 12px; }
.heat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 68px;
  min-height: 52px;
  padding: 6px;
  border-radius: 10px;
  line-height: 1.15;
}
.heat b { font-size: 15px; font-weight: 600; }
.heat small { font-size: 12px; }
.heat.missing { background: #f6f1ea; color: var(--muted); }
.freq {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.freq article { padding: 4px 4px 12px; }
.freq-bar { display: flex; height: 14px; border-radius: 99px; overflow: hidden; background: #f0e9e0; }
.freq-bar span { display: block; height: 100%; }
.split { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; margin-top: 8px; }
.hbar {
  display: grid;
  grid-template-columns: minmax(108px, 170px) 1fr auto;
  gap: 12px;
  align-items: center;
  margin: 9px 0;
}
.hbar.wide { grid-template-columns: minmax(160px, 280px) 1fr auto; }
.hbar-name { font-size: 14px; }
.hbar-track { height: 10px; border-radius: 99px; background: #f0e9e0; }
.hbar-fill { height: 10px; border-radius: 99px; background: var(--berry); }
.hbar-meta { color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; white-space: nowrap; }
@media (max-width: 800px) {
  h1 { font-size: 40px; }
  .kpis, .freq, .split { grid-template-columns: 1fr; }
  .hbar, .hbar.wide { grid-template-columns: 1fr; gap: 4px; }
}
"""


class Order:
    def __init__(self, index: int, row: dict[str, str]) -> None:
        self.index = index
        self.client_name = row["client_name"].strip()
        self.phones = extract_phones(row["phone"])
        self.name_key = distinctive_name(row["client_name"])
        self.date = date.fromisoformat(row["date"])
        self.month = row["date"][:7]
        self.price = Decimal(row["cake_price"]) if row["cake_price"] else Decimal("0")
        self.priced = bool(row["cake_price"])
        self.fulfillment = row["fulfillment"]
        self.payment_type = row["payment_type"]
        self.flowwow = flag(row["is_flowwow"])
        self.website = flag(row["is_website"])
        self.whatsapp = flag(row["is_whatsapp"])
        self.filling = row["filling"].strip()
        self.customer_key = ""


class Customer:
    def __init__(self, key: str) -> None:
        self.key = key
        self.orders: list[Order] = []


def zero_money() -> Decimal:
    return Decimal("0")


def flag(value: str) -> bool:
    if value == "1":
        return True
    if value == "0":
        return False
    raise ValueError(value)


def normalize_name(value: str) -> str:
    text = value.lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", "", text)


def distinctive_name(value: str) -> str:
    normalized = normalize_name(value)
    if normalized in GENERIC_NAMES or len(normalized) < DISTINCTIVE_LENGTH:
        return ""
    return normalized


def extract_phones(raw: str) -> list[str]:
    phones: list[str] = []
    seen: set[str] = set()
    for chunk in raw.split(","):
        digits = re.sub(r"\D", "", chunk)
        if len(digits) < 9:
            continue
        phone = digits[-9:]
        if phone in seen:
            continue
        seen.add(phone)
        phones.append(phone)
    return phones


def normalize_filling(value: str) -> str:
    text = value.lower().replace("ё", "е")
    text = re.sub(r"\s+", " ", text).strip()
    if text == "фисташка и малина":
        return "фисташка малина"
    return text


def find(parent: dict[str, str], phone: str) -> str:
    root = phone
    while parent[root] != root:
        root = parent[root]
    current = phone
    while parent[current] != root:
        nxt = parent[current]
        parent[current] = root
        current = nxt
    return root


def union(parent: dict[str, str], left: str, right: str) -> None:
    left_root = find(parent, left)
    right_root = find(parent, right)
    if left_root == right_root:
        return
    if left_root < right_root:
        parent[right_root] = left_root
    else:
        parent[left_root] = right_root


def union_all(parent: dict[str, str], phones: list[str]) -> None:
    if len(phones) < 2:
        return
    head = phones[0]
    for phone in phones[1:]:
        union(parent, head, phone)


def customer_key(order: Order, parent: dict[str, str], name_phones: dict[str, set[str]]) -> str:
    if order.phones:
        return "p:" + find(parent, order.phones[0])
    if order.name_key and name_phones[order.name_key]:
        phone = sorted(name_phones[order.name_key])[0]
        return "p:" + find(parent, phone)
    if order.name_key:
        return "n:" + order.name_key
    return ""


def load_orders(path: Path) -> list[Order]:
    with path.open(encoding="utf-8", newline="") as handle:
        orders: list[Order] = []
        index = 0
        for row in csv.DictReader(handle):
            if row["deleted"] == "1":
                continue
            orders.append(Order(index, row))
            index += 1
        return orders


def link_customers(orders: list[Order]) -> dict[str, Customer]:
    parent: dict[str, str] = {}
    name_phones: dict[str, set[str]] = defaultdict(set)
    for order in orders:
        for phone in order.phones:
            if phone not in parent:
                parent[phone] = phone
        union_all(parent, order.phones)
        if order.name_key:
            name_phones[order.name_key].update(order.phones)
    for phones in name_phones.values():
        ordered = sorted(phones)
        for phone in ordered:
            if phone not in parent:
                parent[phone] = phone
        union_all(parent, ordered)
    customers: dict[str, Customer] = {}
    for order in orders:
        key = customer_key(order, parent, name_phones)
        order.customer_key = key
        if not key:
            continue
        if key not in customers:
            customers[key] = Customer(key)
        customers[key].orders.append(order)
    for customer in customers.values():
        customer.orders.sort(key=lambda item: (item.date, item.index))
    return customers


def customer_revenue(customer: Customer) -> Decimal:
    return sum((order.price for order in customer.orders), Decimal("0"))


def display_name(customer: Customer) -> str:
    counts: dict[str, int] = defaultdict(int)
    for order in customer.orders:
        normalized = normalize_name(order.client_name)
        if not normalized or normalized in GENERIC_NAMES:
            continue
        counts[order.client_name] += 1
    if not counts:
        return "—"
    ranked = sorted(counts, key=lambda name: (-counts[name], -len(name), name.lower()))
    return ranked[0]


def format_phone(phone: str) -> str:
    return f"{phone[:3]} {phone[3:6]} {phone[6:]}"


def display_phones(customer: Customer) -> str:
    phones: set[str] = set()
    for order in customer.orders:
        phones.update(order.phones)
    if not phones:
        return "—"
    return ", ".join(format_phone(phone) for phone in sorted(phones))


def format_money(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    negative = quantized < 0
    whole, frac = f"{abs(quantized):.2f}".split(".")
    parts: list[str] = []
    while whole:
        parts.append(whole[-3:])
        whole = whole[:-3]
    sign = "−" if negative else ""
    return f"{sign}{' '.join(reversed(parts))}.{frac} ₾"


def format_percent(part: int, whole: int) -> str:
    if whole == 0:
        return "0%"
    return f"{part * 100 / whole:.0f}%"


def format_share(part: Decimal, whole: Decimal) -> str:
    if whole == 0:
        return "0%"
    return f"{float(part / whole * 100):.0f}%"


def format_day(value: date) -> str:
    return f"{value.day:02d}.{value.month:02d}.{value.year}"


def format_long(value: date) -> str:
    return f"{value.day} {MONTH_NAMES[value.month]} {value.year}"


def month_title(month: str) -> str:
    year, month_number = month.split("-")
    return f"{MONTH_NAMES[int(month_number)]} {year}"


def month_short(month: str) -> str:
    year, month_number = month.split("-")
    return f"{SHORT_MONTHS[int(month_number)]} {year[2:]}"


def month_index(month: str) -> int:
    year, month_number = month.split("-")
    return int(year) * 12 + int(month_number)


def plural(count: int, one: str, few: str, many: str) -> str:
    number = abs(count) % 100
    tail = number % 10
    if 11 <= number <= 14:
        word = many
    elif tail == 1:
        word = one
    elif 2 <= tail <= 4:
        word = few
    else:
        word = many
    return f"{count} {word}"


def average_check(orders: list[Order]) -> Decimal:
    priced = [order for order in orders if order.priced]
    if not priced:
        return Decimal("0")
    total = sum((order.price for order in priced), Decimal("0"))
    return (total / len(priced)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def median(values: list[int]) -> int:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


def nice_ceiling(value: float) -> float:
    if value <= 0:
        return 1.0
    base = value * 1.08
    exponent = 0
    while base >= 10:
        base /= 10
        exponent += 1
    while base < 1:
        base *= 10
        exponent -= 1
    for step in (1, 2, 5):
        if base <= step:
            return step * (10**exponent)
    return 10 * (10**exponent)


def format_axis(value: float, money: bool) -> str:
    if money and abs(value) >= 1000:
        thousands = value / 1000
        if abs(thousands - round(thousands)) < 0.05:
            return f"{round(thousands):.0f} тыс."
        return f"{thousands:.1f} тыс."
    if abs(value - round(value)) < 0.05:
        return f"{round(value):.0f}"
    return f"{value:.1f}"


def svg_chart(
    labels: list[str],
    series: list[tuple[str, str, list[float]]],
    stacked: bool,
    money: bool,
    show_values: bool,
    title: str,
) -> str:
    width = 840
    height = 300
    pad_left = 58
    pad_right = 12
    pad_top = 26
    pad_bottom = 42
    inner_w = width - pad_left - pad_right
    inner_h = height - pad_top - pad_bottom
    count = len(labels)
    peak = 0.0
    for index in range(count):
        if stacked:
            total = 0.0
            for _name, _color, values in series:
                total += values[index]
            peak = max(peak, total)
        else:
            for _name, _color, values in series:
                peak = max(peak, values[index])
    ceiling = nice_ceiling(peak)
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" style="font-family:Avenir Next,Segoe UI,sans-serif">',
        f"<title>{html.escape(title)}</title>",
    ]
    for step in range(5):
        tick = ceiling * step / 4
        y = pad_top + inner_h - (tick / ceiling) * inner_h
        parts.append(
            f'<line x1="{pad_left}" y1="{y:.1f}" x2="{width - pad_right}" y2="{y:.1f}" stroke="{COLOR_LINE}"/>'
        )
        parts.append(
            f'<text x="{pad_left - 8}" y="{y + 4:.1f}" text-anchor="end" fill="{COLOR_MUTED}" font-size="11">{html.escape(format_axis(tick, money))}</text>'
        )
    group_w = inner_w / count
    series_count = len(series)
    bar_w = group_w * 0.58 if stacked else group_w / (series_count + 0.7)
    for index, label in enumerate(labels):
        group_x = pad_left + index * group_w
        parts.append(
            f'<text x="{group_x + group_w / 2:.1f}" y="{height - 16}" text-anchor="middle" fill="{COLOR_MUTED}" font-size="12">{html.escape(label)}</text>'
        )
        if stacked:
            cursor = 0.0
            x = group_x + (group_w - bar_w) / 2
            total = 0.0
            for _name, color, values in series:
                value = values[index]
                total += value
                bar_h = (value / ceiling) * inner_h
                y = pad_top + inner_h - ((cursor + value) / ceiling) * inner_h
                cursor += value
                parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{color}"/>'
                )
            if show_values:
                top = pad_top + inner_h - (total / ceiling) * inner_h
                parts.append(
                    f'<text x="{x + bar_w / 2:.1f}" y="{top - 6:.1f}" text-anchor="middle" fill="{COLOR_INK}" font-size="11">{html.escape(format_axis(total, money))}</text>'
                )
            continue
        origin = group_x + (group_w - bar_w * series_count) / 2
        for series_index, (_name, color, values) in enumerate(series):
            value = values[index]
            x = origin + series_index * bar_w
            bar_h = (value / ceiling) * inner_h
            y = pad_top + inner_h - bar_h
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w - 3:.1f}" height="{bar_h:.1f}" rx="3" fill="{color}"/>'
            )
            if show_values:
                parts.append(
                    f'<text x="{x + (bar_w - 3) / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" fill="{COLOR_INK}" font-size="11">{html.escape(format_axis(value, money))}</text>'
                )
    parts.append("</svg>")
    return "".join(parts)


def legend(series: list[tuple[str, str, list[float]]]) -> str:
    items = []
    for name, color, _values in series:
        items.append(
            f'<span class="legend-item"><i style="background:{html.escape(color)}"></i>{html.escape(name)}</span>'
        )
    return f'<div class="legend">{"".join(items)}</div>'


def heat_style(part: int, whole: int) -> str:
    ratio = 0.0 if whole == 0 else part / whole
    alpha = 0.08 + 0.88 * ratio
    color = "#fffdf9" if ratio >= 0.55 else COLOR_INK
    return f"background:rgba(143,61,75,{alpha:.3f});color:{color}"


def cohort_table(customers: dict[str, Customer], max_month: str) -> str:
    groups: dict[str, list[Customer]] = defaultdict(list)
    for customer in customers.values():
        groups[customer.orders[0].month].append(customer)
    months = sorted(groups)
    if not months:
        return "<p class='note'>Нет клиентов.</p>"
    max_index = month_index(max_month)
    offsets = list(range(max_index - month_index(months[0]) + 1))
    header = "".join(f"<th>{offset} мес.</th>" for offset in offsets)
    rows: list[str] = []
    for month in months:
        members = groups[month]
        returned_at: list[int] = []
        first_index = month_index(month)
        for customer in members:
            latest = 0
            for order in customer.orders:
                latest = max(latest, month_index(order.month) - first_index)
            returned_at.append(latest)
        cells: list[str] = []
        for offset in offsets:
            observed = first_index + offset <= max_index
            if not observed:
                cells.append('<td><span class="heat missing">—</span></td>')
                continue
            count = sum(1 for latest in returned_at if latest >= offset)
            cells.append(
                f'<td><span class="heat" style="{heat_style(count, len(members))}"><b>{format_percent(count, len(members))}</b><small>{count}</small></span></td>'
            )
        rows.append(
            f'<tr><th scope="row">{html.escape(month_title(month))}<small>{plural(len(members), "клиент", "клиента", "клиентов")}</small></th>{"".join(cells)}</tr>'
        )
    return (
        '<div class="table-wrap"><table class="cohort"><thead><tr><th></th>'
        + header
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def customer_table(customers: list[Customer]) -> str:
    if not customers:
        return "<p class='note'>Нет клиентов.</p>"
    rows = []
    for customer in customers:
        rows.append(
            "<tr>"
            f"<td>{html.escape(display_name(customer))}</td>"
            f"<td>{html.escape(display_phones(customer))}</td>"
            f"<td class='num'>{len(customer.orders)}</td>"
            f"<td class='num'>{html.escape(format_money(customer_revenue(customer)))}</td>"
            f"<td>{format_day(customer.orders[0].date)}</td>"
            f"<td>{format_day(customer.orders[-1].date)}</td>"
            "</tr>"
        )
    return (
        "<div class='table-wrap'><table><thead><tr>"
        "<th>Имя</th><th>Телефон</th><th class='num'>Заказы</th><th class='num'>Сумма</th><th>Первый</th><th>Последний</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def horizontal_bars(rows: list[tuple[str, int, Decimal]], wide: bool) -> str:
    if not rows:
        return "<p class='note'>Нет данных.</p>"
    max_count = max(count for _label, count, _revenue in rows)
    css = "hbar wide" if wide else "hbar"
    parts = []
    for label, count, revenue in rows:
        width = 0.0 if max_count == 0 else count / max_count * 100
        parts.append(
            f'<div class="{css}">'
            f'<div class="hbar-name">{html.escape(label)}</div>'
            f'<div class="hbar-track"><div class="hbar-fill" style="width:{width:.1f}%"></div></div>'
            f'<div class="hbar-meta">{count} · {html.escape(format_money(revenue))}</div>'
            "</div>"
        )
    return "".join(parts)


def category_rows(orders: list[Order], labels: dict[str, str], field: str) -> list[tuple[str, int, Decimal]]:
    counts: dict[str, int] = defaultdict(int)
    revenue: dict[str, Decimal] = defaultdict(zero_money)
    for order in orders:
        if field == "payment":
            raw = order.payment_type
            label = labels[raw]
        else:
            raw = order.fulfillment
            label = labels[raw]
        counts[label] += 1
        revenue[label] += order.price
    return sorted(((label, counts[label], revenue[label]) for label in counts), key=lambda item: (-item[1], item[0]))


def channel_rows(orders: list[Order]) -> list[tuple[str, int, Decimal]]:
    groups = (
        ("Flowwow", [order for order in orders if order.flowwow]),
        ("Сайт", [order for order in orders if order.website]),
        ("WhatsApp", [order for order in orders if order.whatsapp]),
        (
            "Не указан",
            [order for order in orders if not order.flowwow and not order.website and not order.whatsapp],
        ),
    )
    rows: list[tuple[str, int, Decimal]] = []
    for label, items in groups:
        revenue = sum((order.price for order in items), Decimal("0"))
        rows.append((label, len(items), revenue))
    return rows


def channel_bars(orders: list[Order]) -> str:
    rows = channel_rows(orders)
    if not rows:
        return "<p class='note'>Нет данных.</p>"
    max_count = max(count for _label, count, _revenue in rows)
    parts = []
    for label, count, revenue in rows:
        width = 0.0 if max_count == 0 else count / max_count * 100
        parts.append(
            '<div class="hbar">'
            f'<div class="hbar-name">{html.escape(label)}</div>'
            f'<div class="hbar-track"><div class="hbar-fill" style="width:{width:.1f}%"></div></div>'
            f'<div class="hbar-meta">{count} / {format_percent(count, len(orders))} · {html.escape(format_money(revenue))}</div>'
            "</div>"
        )
    return "".join(parts)


def channel_month_table(
    months: list[str],
    totals: dict[str, int],
    series: list[tuple[str, dict[str, int]]],
) -> str:
    header = "".join(f"<th class='num'>{html.escape(name)}</th>" for name, _counts in series)
    rows: list[str] = []
    for month in months:
        cells = "".join(
            f"<td class='num'>{counts[month]} / {format_percent(counts[month], totals[month])}</td>"
            for _name, counts in series
        )
        rows.append(f"<tr><td>{html.escape(month_title(month))}</td>{cells}</tr>")
    return (
        "<div class='table-wrap'><table><thead><tr><th>Месяц</th>"
        + header
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def filling_rows(orders: list[Order]) -> list[tuple[str, int, Decimal]]:
    grouped: dict[str, list[Order]] = defaultdict(list)
    for order in orders:
        key = normalize_filling(order.filling)
        if not key:
            continue
        grouped[key].append(order)
    ranked = sorted(grouped, key=lambda key: (-len(grouped[key]), key))[:FILLING_LIMIT]
    rows: list[tuple[str, int, Decimal]] = []
    for key in ranked:
        items = grouped[key]
        label_counts: dict[str, int] = defaultdict(int)
        for order in items:
            label_counts[order.filling] += 1
        label = sorted(label_counts, key=lambda name: (-label_counts[name], name))[0]
        revenue = sum((order.price for order in items), Decimal("0"))
        rows.append((label, len(items), revenue))
    return rows


def gap_bins(gaps: list[int]) -> list[int]:
    counts = []
    for low, high, _label in GAP_BINS:
        counts.append(sum(1 for gap in gaps if low <= gap <= high))
    return counts


def month_numbers(months: list[str], values: dict[str, int]) -> list[float]:
    return [float(values[month]) for month in months]


def render(orders: list[Order], customers: dict[str, Customer]) -> str:
    first = min(order.date for order in orders)
    last = max(order.date for order in orders)
    months = sorted({order.month for order in orders})
    revenue = sum((order.price for order in orders), Decimal("0"))
    repeat_customers = [customer for customer in customers.values() if len(customer.orders) >= 2]
    repeat_orders: list[Order] = []
    for customer in repeat_customers:
        repeat_orders.extend(customer.orders)
    repeat_revenue = sum((customer_revenue(customer) for customer in repeat_customers), Decimal("0"))
    new_orders: dict[str, int] = defaultdict(int)
    return_orders: dict[str, int] = defaultdict(int)
    new_revenue: dict[str, Decimal] = defaultdict(zero_money)
    return_revenue: dict[str, Decimal] = defaultdict(zero_money)
    for customer in customers.values():
        for index, order in enumerate(customer.orders):
            if index == 0:
                new_orders[order.month] += 1
                new_revenue[order.month] += order.price
            else:
                return_orders[order.month] += 1
                return_revenue[order.month] += order.price
    flowwow_orders: dict[str, int] = defaultdict(int)
    website_orders: dict[str, int] = defaultdict(int)
    whatsapp_orders: dict[str, int] = defaultdict(int)
    other_orders: dict[str, int] = defaultdict(int)
    month_totals: dict[str, int] = defaultdict(int)
    for order in orders:
        month_totals[order.month] += 1
        if order.flowwow:
            flowwow_orders[order.month] += 1
        if order.website:
            website_orders[order.month] += 1
        if order.whatsapp:
            whatsapp_orders[order.month] += 1
        if not order.flowwow and not order.website and not order.whatsapp:
            other_orders[order.month] += 1
    labels = [month_short(month) for month in months]
    movement = [
        ("Новые", COLOR_NEW, month_numbers(months, new_orders)),
        ("Вернувшиеся", COLOR_RETURN, month_numbers(months, return_orders)),
    ]
    movement_money = [
        ("Новые", COLOR_NEW, [float(new_revenue[month]) for month in months]),
        ("Вернувшиеся", COLOR_RETURN, [float(return_revenue[month]) for month in months]),
    ]
    channels = [
        ("Flowwow", COLOR_RETURN, month_numbers(months, flowwow_orders)),
        ("Сайт", COLOR_NEW, month_numbers(months, website_orders)),
        ("WhatsApp", COLOR_WHATSAPP, month_numbers(months, whatsapp_orders)),
        ("Не указан", COLOR_UNKNOWN, month_numbers(months, other_orders)),
    ]
    channel_counts = [
        ("Flowwow", flowwow_orders),
        ("Сайт", website_orders),
        ("WhatsApp", whatsapp_orders),
        ("Не указан", other_orders),
    ]
    gaps = [
        (customer.orders[1].date - customer.orders[0].date).days
        for customer in customers.values()
        if len(customer.orders) >= 2
    ]
    once = sum(1 for customer in customers.values() if len(customer.orders) == 1)
    twice = sum(1 for customer in customers.values() if len(customer.orders) == 2)
    more = sum(1 for customer in customers.values() if len(customer.orders) >= 3)
    once_revenue = sum(
        (customer_revenue(customer) for customer in customers.values() if len(customer.orders) == 1),
        Decimal("0"),
    )
    twice_revenue = sum(
        (customer_revenue(customer) for customer in customers.values() if len(customer.orders) == 2),
        Decimal("0"),
    )
    more_revenue = sum(
        (customer_revenue(customer) for customer in customers.values() if len(customer.orders) >= 3),
        Decimal("0"),
    )
    by_revenue = sorted(
        customers.values(),
        key=lambda customer: (customer_revenue(customer), len(customer.orders), customer.key),
        reverse=True,
    )[:TOP_LIMIT]
    by_orders = sorted(
        customers.values(),
        key=lambda customer: (len(customer.orders), customer_revenue(customer), customer.key),
        reverse=True,
    )[:TOP_LIMIT]
    movement_rows = []
    for month in months:
        movement_rows.append(
            "<tr>"
            f"<td>{html.escape(month_title(month))}</td>"
            f"<td class='num'>{new_orders[month]}</td>"
            f"<td class='num'>{html.escape(format_money(new_revenue[month]))}</td>"
            f"<td class='num'>{return_orders[month]} / {format_percent(return_orders[month], new_orders[month] + return_orders[month])}</td>"
            f"<td class='num'>{html.escape(format_money(return_revenue[month]))} / {format_share(return_revenue[month], new_revenue[month] + return_revenue[month])}</td>"
            "</tr>"
        )
    customer_count = len(customers)
    if gaps:
        bin_counts = gap_bins(gaps)
        gap_block = (
            svg_chart(
                [label for _low, _high, label in GAP_BINS],
                [("Клиенты", COLOR_RETURN, [float(count) for count in bin_counts])],
                False,
                False,
                True,
                "Дни между первым и вторым заказом",
            )
            + f"<p class='note'>Медиана — {plural(median(gaps), 'день', 'дня', 'дней')}. "
            + f"Повторный заказ есть у {plural(len(gaps), 'клиента', 'клиентов', 'клиентов')}.</p>"
        )
    else:
        gap_block = "<p class='note'>Повторных заказов нет.</p>"
    freq_total = customer_count
    freq_widths = [
        0.0 if freq_total == 0 else once / freq_total * 100,
        0.0 if freq_total == 0 else twice / freq_total * 100,
        0.0 if freq_total == 0 else more / freq_total * 100,
    ]
    page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Заказы и ретеншен</title>
<style>{CSS}</style>
</head>
<body>
<main>
<header class="hero">
<p class="eyebrow">{html.escape(format_long(first))} — {html.escape(format_long(last))}</p>
<h1>Заказы и ретеншен</h1>
<p class="lede">Клиент определяется по телефону: номер приводится к 9 цифрам, несколько номеров в одном заказе считаются одним человеком. Имя связывает разные номера, только если после нормализации в нём не меньше 10 символов. Каналы «флао», «флоу», «сайт», «вотсап», «смм» и «инст» клиентом не считаются. Удалённые заказы исключены.</p>
</header>
<div class="kpis">
<article class="kpi"><p class="label">Заказы</p><p class="value">{len(orders)}</p><p class="hint">без удалённых</p></article>
<article class="kpi"><p class="label">Выручка</p><p class="value">{html.escape(format_money(revenue))}</p><p class="hint">{html.escape(format_long(first))} — {html.escape(format_long(last))}</p></article>
<article class="kpi"><p class="label">Средний чек</p><p class="value">{html.escape(format_money(average_check(orders)))}</p><p class="hint">по заказам, где указана цена</p></article>
<article class="kpi"><p class="label">Клиенты</p><p class="value">{customer_count}</p></article>
<article class="kpi"><p class="label">Повторные</p><p class="value">{format_percent(len(repeat_customers), customer_count)}</p><p class="hint">{len(repeat_customers)} из {customer_count}</p></article>
<article class="kpi"><p class="label">Выручка повторных</p><p class="value">{format_share(repeat_revenue, revenue)}</p><p class="hint">{html.escape(format_money(repeat_revenue))}</p></article>
</div>
<section>
<h2>Новые и вернувшиеся</h2>
<p class="note">Вернувшийся заказ — не первый у этого клиента.</p>
<h3>Заказы</h3>
{legend(movement)}
{svg_chart(labels, movement, False, False, False, "Новые и вернувшиеся заказы")}
<h3>Выручка</h3>
{legend(movement_money)}
{svg_chart(labels, movement_money, False, True, False, "Выручка новых и вернувшихся")}
<div class="table-wrap"><table><thead><tr><th>Месяц</th><th class="num">Новые</th><th class="num">Выручка</th><th class="num">Вернувшиеся</th><th class="num">Выручка</th></tr></thead><tbody>{"".join(movement_rows)}</tbody></table></div>
</section>
<section>
<h2>Когорты</h2>
<p class="note">Строка — месяц первого заказа. В ячейке доля и число клиентов, которые заказали в этом месяце или позже. Прочерк — такого месяца в данных ещё нет. Ноль — месяц был, повторных заказов нет.</p>
{cohort_table(customers, months[-1])}
</section>
<section>
<h2>До второго заказа</h2>
<p class="note">Дни между первым и вторым заказом.</p>
{gap_block}
</section>
<section>
<h2>Как часто заказывают</h2>
<div class="freq">
<article><p class="label">1 заказ</p><p class="value">{once}</p><p class="hint">{format_percent(once, freq_total)} · {html.escape(format_money(once_revenue))}</p></article>
<article><p class="label">2 заказа</p><p class="value">{twice}</p><p class="hint">{format_percent(twice, freq_total)} · {html.escape(format_money(twice_revenue))}</p></article>
<article><p class="label">3 и больше</p><p class="value">{more}</p><p class="hint">{format_percent(more, freq_total)} · {html.escape(format_money(more_revenue))}</p></article>
</div>
<div class="freq-bar"><span style="width:{freq_widths[0]:.1f}%;background:{COLOR_UNKNOWN}"></span><span style="width:{freq_widths[1]:.1f}%;background:#c47b86"></span><span style="width:{freq_widths[2]:.1f}%;background:{COLOR_RETURN}"></span></div>
</section>
<section>
<h2>Клиенты</h2>
<p class="note">Телефон показан как 9 цифр. Несколько номеров одного человека перечислены через запятую.</p>
<h3>По выручке</h3>
{customer_table(by_revenue)}
<h3>По числу заказов</h3>
{customer_table(by_orders)}
</section>
<section>
<h2>Магазин</h2>
<p class="note">Рядом с полосой — число заказов и выручка. Заказ может попасть сразу в несколько каналов.</p>
<h3>Откуда</h3>
{channel_bars(orders)}
{legend(channels)}
{svg_chart(labels, channels, False, False, False, "Откуда заказ по месяцам")}
{channel_month_table(months, month_totals, channel_counts)}
<div class="split">
<div><h3>Выдача</h3>{horizontal_bars(category_rows(orders, FULFILLMENT_LABELS, "fulfillment"), False)}</div>
<div><h3>Оплата</h3>{horizontal_bars(category_rows(orders, PAYMENT_LABELS, "payment"), False)}</div>
</div>
<h3>Начинки</h3>
{horizontal_bars(filling_rows(orders), True)}
<h3>Начинки у повторных</h3>
{horizontal_bars(filling_rows(repeat_orders), True)}
</section>
<p class="footer">Источник — orders_combined.csv</p>
</main>
</body>
</html>
"""
    return page


def main() -> None:
    orders = load_orders(CSV_PATH)
    customers = link_customers(orders)
    HTML_PATH.write_text(render(orders, customers), encoding="utf-8")
    print(HTML_PATH)


if __name__ == "__main__":
    main()
