import re
from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from statistics import median, quantiles
from zoneinfo import ZoneInfo

from crm.models import CrmOrder
from crm.phone import extract_phones

_TB = ZoneInfo("Asia/Tbilisi")
_GENERIC_NAMES = {"флао", "флоу", "сайт", "вотсап", "смм", "инст"}
_DISTINCTIVE_LENGTH = 10
_TOP_LIMIT = 20
_LAPSED_DAYS = 60
_GAP_BINS = (
    (0, 0, "0"),
    (1, 7, "1–7"),
    (8, 14, "8–14"),
    (15, 30, "15–30"),
    (31, 60, "31–60"),
    (61, 90, "61–90"),
    (91, 100000, "91+"),
)
_UNIT_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*"
    r"(килограммов|килограмма|килограмм|кг|kgs|kg|"
    r"граммов|грамма|грамм|грам|gramm|grams|gram|гр|gr|g)"
    r"(?!\w)"
)
_BARE_GRAMS_RE = re.compile(
    r"(?<!\d)(600|700|800|900|1000|1200|1500|1800|2000|2500|3000)(?!\d)"
)
_BARE_NUMBER_RE = re.compile(r"\s*(\d+(?:[.,]\d+)?)\s*")
_MONEY = Decimal("0.01")
_KILO = Decimal("0.001")
_THOUSAND = Decimal("1000")


class Customer:
    def __init__(self, key: str) -> None:
        self.key = key
        self.orders: list[CrmOrder] = []
        self.phones: set[str] = set()


def weight_kg(text: str) -> Decimal | None:
    lowered = text.lower().replace("ё", "е")
    total = Decimal("0")
    found = False
    spans: list[tuple[int, int]] = []
    for match in _UNIT_RE.finditer(lowered):
        spans.append(match.span())
        parsed = _from_unit(Decimal(match.group(1).replace(",", ".")), match.group(2))
        if parsed is None:
            continue
        total += parsed
        found = True
    masked = _mask(lowered, spans)
    for match in _BARE_GRAMS_RE.finditer(masked):
        total += Decimal(match.group(1)) / _THOUSAND
        found = True
    if found:
        return total
    bare = _BARE_NUMBER_RE.fullmatch(lowered)
    if bare is None:
        return None
    value = Decimal(bare.group(1).replace(",", "."))
    if value < 20:
        return value
    grams = int(value)
    if value == grams and grams % 100 == 0 and 500 <= grams <= 8000:
        return Decimal(grams) / _THOUSAND
    return None


def windows(month: str, today: date) -> tuple[date, date, date, date]:
    start, last = _month_bounds(month)
    if start <= today <= last:
        end = today
    else:
        end = last
    prev_start, prev_last = _month_bounds(_previous_month(month))
    if end < last:
        prev_end = date(prev_start.year, prev_start.month, min(end.day, prev_last.day))
    else:
        prev_end = prev_last
    return start, end, prev_start, prev_end


def pulse(month: str, today: date) -> dict:
    start, end, prev_start, prev_end = windows(month, today)
    orders = _live_orders()
    return {
        "month": month,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "previous_start": prev_start.isoformat(),
        "previous_end": prev_end.isoformat(),
        "current": _totals(_between(orders, start, end)),
        "previous": _totals(_between(orders, prev_start, prev_end)),
        "weeks": _weeks(orders, start, end),
        "weekdays": _weekdays(orders, start, end),
    }


def production(month: str, today: date) -> dict:
    start, end = windows(month, today)[:2]
    orders = _live_orders()
    order_counts, kilograms = _daily_series(orders)
    return {
        "month": month,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "baseline": _baseline(order_counts, kilograms),
        "days": _days(orders, start, end),
        "slots": _slots(orders),
        "lead": _lead(orders),
        "horizon": {
            "today": today.isoformat(),
            "tomorrow": _horizon_day(orders, today + timedelta(days=1)),
            "day_after": _horizon_day(orders, today + timedelta(days=2)),
        },
    }


def clients(today: date) -> dict:
    orders = _live_orders()
    customers, unknown = _link_customers(orders)
    known_orders = len(orders) - unknown
    repeat = [customer for customer in customers.values() if len(customer.orders) >= 2]
    known_revenue = Decimal("0")
    repeat_revenue = Decimal("0")
    for customer in customers.values():
        amount = _revenue(customer.orders)
        known_revenue += amount
        if len(customer.orders) >= 2:
            repeat_revenue += amount
    months = _month_span(orders)
    return {
        "orders": len(orders),
        "known_orders": known_orders,
        "unknown_orders": unknown,
        "clients": len(customers),
        "repeat_clients": len(repeat),
        "known_revenue": _money(known_revenue),
        "repeat_revenue": _money(repeat_revenue),
        "months": _movement(customers, months),
        "cohorts": _cohorts(customers, months),
        "gaps": _gaps(customers),
        "frequency": _frequency(customers),
        "top_revenue": [_customer_row(customer) for customer in _top_revenue(customers)],
        "top_orders": [_customer_row(customer) for customer in _top_orders(customers)],
        "lapsed": [_lapsed_row(customer) for customer in _lapsed(customers, today)],
    }


def _from_unit(value: Decimal, unit: str) -> Decimal | None:
    if unit.startswith("к") or unit.startswith("k"):
        if value < 0 or value > 20:
            return None
        return value
    grams = int(value)
    if value != grams or grams % 100 != 0 or grams < 500 or grams > 8000:
        return None
    return Decimal(grams) / _THOUSAND


def _mask(text: str, spans: list[tuple[int, int]]) -> str:
    chars = list(text)
    for start, end in spans:
        for index in range(start, end):
            chars[index] = " "
    return "".join(chars)


def _money(value: Decimal) -> str:
    return format(value.quantize(_MONEY), "f")


def _num(value: Decimal) -> str:
    text = format(value.quantize(_KILO), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _month_bounds(month: str) -> tuple[date, date]:
    year_str, month_str = month.split("-")
    year = int(year_str)
    month_num = int(month_str)
    return date(year, month_num, 1), date(year, month_num, monthrange(year, month_num)[1])


def _previous_month(month: str) -> str:
    start, _last = _month_bounds(month)
    prev = start - timedelta(days=1)
    return f"{prev.year:04d}-{prev.month:02d}"


def _live_orders() -> list[CrmOrder]:
    return list(CrmOrder.objects.filter(deleted=False).order_by("date", "id"))


def _between(orders: list[CrmOrder], start: date, end: date) -> list[CrmOrder]:
    return [order for order in orders if start <= order.date <= end]


def _order_revenue(order: CrmOrder) -> Decimal:
    return order.cake_price + order.delivery_price


def _revenue(orders: list[CrmOrder]) -> Decimal:
    total = Decimal("0")
    for order in orders:
        total += _order_revenue(order)
    return total


def _totals(orders: list[CrmOrder]) -> dict:
    kilograms = Decimal("0")
    unknown = 0
    for order in orders:
        parsed = weight_kg(order.weight)
        if parsed is None:
            unknown += 1
        else:
            kilograms += parsed
    count = len(orders)
    average = None if count == 0 else _money(_revenue(orders) / count)
    return {
        "orders": count,
        "revenue": _money(_revenue(orders)),
        "average_check": average,
        "kilograms": _num(kilograms),
        "weight_unknown": unknown,
    }


def _week_slices(start: date, end: date) -> list[tuple[date, date]]:
    slices: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        week_end = cursor + timedelta(days=6 - cursor.weekday())
        if week_end > end:
            week_end = end
        slices.append((cursor, week_end))
        cursor = week_end + timedelta(days=1)
    return slices


def _weeks(orders: list[CrmOrder], start: date, end: date) -> list[dict]:
    rows = []
    for week_start, week_end in _week_slices(start, end):
        totals = _totals(_between(orders, week_start, week_end))
        rows.append(
            {
                "start": week_start.isoformat(),
                "end": week_end.isoformat(),
                "orders": totals["orders"],
                "revenue": totals["revenue"],
                "kilograms": totals["kilograms"],
            }
        )
    return rows


def _weekdays(orders: list[CrmOrder], start: date, end: date) -> list[dict]:
    grouped: list[list[CrmOrder]] = [[], [], [], [], [], [], []]
    for order in orders:
        if start <= order.date <= end:
            grouped[order.date.weekday()].append(order)
    rows = []
    for weekday, items in enumerate(grouped):
        totals = _totals(items)
        rows.append(
            {
                "weekday": weekday,
                "orders": totals["orders"],
                "revenue": totals["revenue"],
                "kilograms": totals["kilograms"],
            }
        )
    return rows


def _daily_series(orders: list[CrmOrder]) -> tuple[list[Decimal], list[Decimal]]:
    by_orders: dict[date, int] = defaultdict(int)
    by_kg: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    for order in orders:
        by_orders[order.date] += 1
        parsed = weight_kg(order.weight)
        if parsed is not None:
            by_kg[order.date] += parsed
    days = sorted(by_orders)
    return [Decimal(by_orders[day]) for day in days], [by_kg[day] for day in days]


def _median(values: list[Decimal]) -> Decimal:
    return Decimal(str(median(values)))


def _p90(values: list[Decimal]) -> Decimal:
    if len(values) == 1:
        return values[0]
    raw = quantiles([float(value) for value in values], n=10, method="inclusive")[-1]
    return Decimal(str(raw)).quantize(_KILO)


def _baseline(order_counts: list[Decimal], kilograms: list[Decimal]) -> dict:
    if not order_counts:
        return {
            "days": 0,
            "orders_median": None,
            "orders_p90": None,
            "orders_max": None,
            "kilograms_median": None,
            "kilograms_p90": None,
            "kilograms_max": None,
        }
    return {
        "days": len(order_counts),
        "orders_median": _num(_median(order_counts)),
        "orders_p90": _num(_p90(order_counts)),
        "orders_max": _num(max(order_counts)),
        "kilograms_median": _num(_median(kilograms)),
        "kilograms_p90": _num(_p90(kilograms)),
        "kilograms_max": _num(max(kilograms)),
    }


def _days(orders: list[CrmOrder], start: date, end: date) -> list[dict]:
    by_orders: dict[date, int] = defaultdict(int)
    by_kg: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    by_unknown: dict[date, int] = defaultdict(int)
    for order in _between(orders, start, end):
        by_orders[order.date] += 1
        parsed = weight_kg(order.weight)
        if parsed is None:
            by_unknown[order.date] += 1
        else:
            by_kg[order.date] += parsed
    rows = []
    cursor = start
    while cursor <= end:
        rows.append(
            {
                "date": cursor.isoformat(),
                "orders": by_orders[cursor],
                "kilograms": _num(by_kg[cursor]),
                "weight_unknown": by_unknown[cursor],
            }
        )
        cursor += timedelta(days=1)
    return rows


def _slots(orders: list[CrmOrder]) -> dict:
    interval = 0
    exact = 0
    missing = 0
    morning = 0
    day = 0
    evening = 0
    hours = [0] * 24
    for order in orders:
        if order.time_start is None:
            missing += 1
            continue
        if order.time_end is None:
            exact += 1
        else:
            interval += 1
        hour = order.time_start.hour
        hours[hour] += 1
        if hour < 14:
            morning += 1
        elif hour < 18:
            day += 1
        else:
            evening += 1
    return {
        "interval": interval,
        "exact": exact,
        "missing": missing,
        "morning": morning,
        "day": day,
        "evening": evening,
        "hours": [{"hour": hour, "orders": count} for hour, count in enumerate(hours)],
    }


def _lead_days(order: CrmOrder) -> int:
    return (order.date - order.created_at.astimezone(_TB).date()).days


def _lead(orders: list[CrmOrder]) -> dict:
    if not orders:
        return {"median": None, "same_day": 0, "next_day": 0, "long": 0}
    leads = [_lead_days(order) for order in orders]
    return {
        "median": _num(Decimal(str(median(leads)))),
        "same_day": sum(1 for days in leads if days == 0),
        "next_day": sum(1 for days in leads if days == 1),
        "long": sum(1 for days in leads if days >= 15),
    }


def _horizon_day(orders: list[CrmOrder], day: date) -> dict:
    totals = _totals(_between(orders, day, day))
    return {"date": day.isoformat(), "orders": totals["orders"], "kilograms": totals["kilograms"]}


def _append_phone(value: str, found: list[str], seen: set[str]) -> None:
    digits = re.sub(r"\D", "", value)
    if len(digits) < 9:
        return
    phone = digits[-9:]
    if phone in seen:
        return
    seen.add(phone)
    found.append(phone)


def order_phones(order: CrmOrder) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for entry in order.phones:
        value = entry["value"]
        if value.startswith("tg:"):
            continue
        _append_phone(value, found, seen)
    for text in (order.contact, order.nickname):
        for digits in extract_phones(text):
            _append_phone(digits, found, seen)
    return found


def name_key(value: str) -> str:
    stripped = re.sub(r"\d+", "", value)
    normalized = re.sub(r"[^a-zа-я0-9]+", "", stripped.lower().replace("ё", "е"))
    if normalized in _GENERIC_NAMES or len(normalized) < _DISTINCTIVE_LENGTH:
        return ""
    return normalized


def _find(parent: dict[str, str], phone: str) -> str:
    root = phone
    while parent[root] != root:
        root = parent[root]
    current = phone
    while parent[current] != root:
        nxt = parent[current]
        parent[current] = root
        current = nxt
    return root


def _union(parent: dict[str, str], left: str, right: str) -> None:
    left_root = _find(parent, left)
    right_root = _find(parent, right)
    if left_root == right_root:
        return
    if left_root < right_root:
        parent[right_root] = left_root
    else:
        parent[left_root] = right_root


def _link_customers(orders: list[CrmOrder]) -> tuple[dict[str, Customer], int]:
    parent: dict[str, str] = {}
    name_phones: dict[str, set[str]] = defaultdict(set)
    phones_by_id: dict[int, list[str]] = {}
    for order in orders:
        phones = order_phones(order)
        phones_by_id[order.id] = phones
        for phone in phones:
            parent.setdefault(phone, phone)
        if len(phones) >= 2:
            head = phones[0]
            for phone in phones[1:]:
                _union(parent, head, phone)
        if phones:
            for source in (order.nickname, order.contact):
                key = name_key(source)
                if key:
                    name_phones[key].update(phones)
    for phones in name_phones.values():
        ordered = sorted(phones)
        for phone in ordered:
            parent.setdefault(phone, phone)
        if len(ordered) >= 2:
            head = ordered[0]
            for phone in ordered[1:]:
                _union(parent, head, phone)
    customers: dict[str, Customer] = {}
    unknown = 0
    for order in orders:
        phones = phones_by_id[order.id]
        if not phones:
            unknown += 1
            continue
        key = "p:" + _find(parent, phones[0])
        if key not in customers:
            customers[key] = Customer(key)
        customers[key].orders.append(order)
        customers[key].phones.update(phones)
    return customers, unknown


def _label(value: str) -> str:
    text = re.sub(r"\d{7,}", " ", value)
    return re.sub(r"\s+", " ", text).strip(" ,.-")


def _display_name(orders: list[CrmOrder]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for order in orders:
        for source in (order.nickname, order.contact):
            label = _label(source)
            normalized = re.sub(r"[^a-zа-я0-9]+", "", label.lower().replace("ё", "е"))
            if not normalized or normalized in _GENERIC_NAMES:
                continue
            counts[label] += 1
    if not counts:
        return ""
    return sorted(counts, key=lambda name: (-counts[name], -len(name), name.lower()))[0]


def _customer_row(customer: Customer) -> dict:
    return {
        "name": _display_name(customer.orders),
        "phones": sorted(customer.phones),
        "orders": len(customer.orders),
        "revenue": _money(_revenue(customer.orders)),
        "first": customer.orders[0].date.isoformat(),
        "last": customer.orders[-1].date.isoformat(),
        "order_id": customer.orders[-1].id,
    }


def _lapsed_row(customer: Customer) -> dict:
    order = customer.orders[0]
    return {
        "name": _display_name(customer.orders),
        "phones": sorted(customer.phones),
        "revenue": _money(_order_revenue(order)),
        "date": order.date.isoformat(),
        "order_id": order.id,
    }


def _top_revenue(customers: dict[str, Customer]) -> list[Customer]:
    return sorted(
        customers.values(),
        key=lambda customer: (_revenue(customer.orders), len(customer.orders), customer.key),
        reverse=True,
    )[:_TOP_LIMIT]


def _top_orders(customers: dict[str, Customer]) -> list[Customer]:
    return sorted(
        customers.values(),
        key=lambda customer: (len(customer.orders), _revenue(customer.orders), customer.key),
        reverse=True,
    )[:_TOP_LIMIT]


def _lapsed(customers: dict[str, Customer], today: date) -> list[Customer]:
    cutoff = today - timedelta(days=_LAPSED_DAYS)
    rows = [
        customer
        for customer in customers.values()
        if len(customer.orders) == 1 and customer.orders[0].date < cutoff
    ]
    return sorted(
        rows,
        key=lambda customer: (_order_revenue(customer.orders[0]), customer.orders[0].id),
        reverse=True,
    )


def _month_span(orders: list[CrmOrder]) -> list[str]:
    if not orders:
        return []
    year = orders[0].date.year
    month = orders[0].date.month
    last = orders[-1].date
    months = []
    while (year, month) <= (last.year, last.month):
        months.append(f"{year:04d}-{month:02d}")
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return months


def _movement(customers: dict[str, Customer], months: list[str]) -> list[dict]:
    new_orders: dict[str, int] = defaultdict(int)
    return_orders: dict[str, int] = defaultdict(int)
    new_revenue: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    return_revenue: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for customer in customers.values():
        for index, order in enumerate(customer.orders):
            month = f"{order.date.year:04d}-{order.date.month:02d}"
            amount = _order_revenue(order)
            if index == 0:
                new_orders[month] += 1
                new_revenue[month] += amount
            else:
                return_orders[month] += 1
                return_revenue[month] += amount
    return [
        {
            "month": month,
            "new_orders": new_orders[month],
            "new_revenue": _money(new_revenue[month]),
            "return_orders": return_orders[month],
            "return_revenue": _money(return_revenue[month]),
        }
        for month in months
    ]


def _month_index(month: str) -> int:
    year_str, month_str = month.split("-")
    return int(year_str) * 12 + int(month_str)


def _cohorts(customers: dict[str, Customer], months: list[str]) -> list[dict]:
    groups: dict[str, list[Customer]] = defaultdict(list)
    for customer in customers.values():
        first = customer.orders[0].date
        groups[f"{first.year:04d}-{first.month:02d}"].append(customer)
    cohort_months = sorted(groups)
    if not cohort_months or not months:
        return []
    max_index = _month_index(months[-1])
    offsets = list(range(max_index - _month_index(cohort_months[0]) + 1))
    rows = []
    for month in cohort_months:
        members = groups[month]
        first_index = _month_index(month)
        latest = []
        for customer in members:
            last_offset = 0
            for order in customer.orders:
                order_month = f"{order.date.year:04d}-{order.date.month:02d}"
                last_offset = max(last_offset, _month_index(order_month) - first_index)
            latest.append(last_offset)
        cells = []
        for offset in offsets:
            observed = first_index + offset <= max_index
            if not observed:
                cells.append({"offset": offset, "count": None, "share": None, "observed": False})
                continue
            count = sum(1 for value in latest if value >= offset)
            cells.append(
                {
                    "offset": offset,
                    "count": count,
                    "share": _num(Decimal(count) / Decimal(len(members))),
                    "observed": True,
                }
            )
        rows.append({"month": month, "clients": len(members), "cells": cells})
    return rows


def _gaps(customers: dict[str, Customer]) -> dict:
    gaps = [
        (customer.orders[1].date - customer.orders[0].date).days
        for customer in customers.values()
        if len(customer.orders) >= 2
    ]
    bins = []
    for low, high, label in _GAP_BINS:
        bins.append({"label": label, "count": sum(1 for gap in gaps if low <= gap <= high)})
    return {
        "median": None if not gaps else _num(Decimal(str(median(gaps)))),
        "bins": bins,
    }


def _frequency(customers: dict[str, Customer]) -> dict:
    once = [customer for customer in customers.values() if len(customer.orders) == 1]
    twice = [customer for customer in customers.values() if len(customer.orders) == 2]
    more = [customer for customer in customers.values() if len(customer.orders) >= 3]
    return {
        "once": {"clients": len(once), "revenue": _money(_group_revenue(once))},
        "twice": {"clients": len(twice), "revenue": _money(_group_revenue(twice))},
        "more": {"clients": len(more), "revenue": _money(_group_revenue(more))},
    }


def _group_revenue(customers: list[Customer]) -> Decimal:
    total = Decimal("0")
    for customer in customers:
        total += _revenue(customer.orders)
    return total
