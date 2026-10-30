import re
from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from statistics import median, quantiles
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.utils import timezone

from accounts.models import UserProfile, chef_identity
from attendance.models import AttendanceEvent
from attendance.salary import compute_day_worked_seconds, daily_monthly_share
from crm.models import AnalyticsOrderComposition, CrmOrder, CrmOrderEvent
from crm.phone import extract_phones

_TB = ZoneInfo("Asia/Tbilisi")
_GENERIC_NAMES = {"флао", "флоу", "сайт", "вотсап", "смм", "инст"}
_DISTINCTIVE_LENGTH = 10
_NICKNAME_LENGTH = 4
_TOP_LIMIT = 20
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


def overview(today: date) -> dict:
    orders = _live_orders()
    months = _month_span(orders)
    current_month = f"{today.year:04d}-{today.month:02d}"
    totals = _totals(orders)
    totals["months"] = len(months)
    return {
        "first_date": None if not orders else orders[0].date.isoformat(),
        "today": today.isoformat(),
        "current_month": current_month,
        "totals": totals,
        "months": _overview_months(orders, months, current_month),
        "channels": _overview_channels(orders, months),
        "payments": _overview_payments(orders),
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


def clients() -> dict:
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


def _month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def _channel(order: CrmOrder) -> str:
    if order.flowwow_order_id is not None or order.payment_type == CrmOrder.PAYMENT_FLOWWOW:
        return "flowwow"
    if order.website_order_id is not None:
        return "website"
    return "direct"


def _price_per_kg(orders: list[CrmOrder]) -> str | None:
    revenue = Decimal("0")
    kilograms = Decimal("0")
    for order in orders:
        parsed = weight_kg(order.weight)
        if parsed is None:
            continue
        revenue += _order_revenue(order)
        kilograms += parsed
    if kilograms == 0:
        return None
    return _money(revenue / kilograms)


def _overview_months(orders: list[CrmOrder], months: list[str], current_month: str) -> list[dict]:
    grouped: dict[str, list[CrmOrder]] = defaultdict(list)
    for order in orders:
        grouped[_month_key(order.date)].append(order)
    rows = []
    for month in months:
        items = grouped[month]
        totals = _totals(items)
        rows.append(
            {
                "month": month,
                "orders": totals["orders"],
                "revenue": totals["revenue"],
                "average_check": totals["average_check"],
                "kilograms": totals["kilograms"],
                "weight_unknown": totals["weight_unknown"],
                "price_per_kg": _price_per_kg(items),
                "partial": month == current_month,
            }
        )
    return rows


def _overview_channels(orders: list[CrmOrder], months: list[str]) -> list[dict]:
    names = ("flowwow", "website", "direct")
    counts: dict[str, dict[str, int]] = {name: defaultdict(int) for name in names}
    revenue: dict[str, dict[str, Decimal]] = {name: defaultdict(lambda: Decimal("0")) for name in names}
    for order in orders:
        month = _month_key(order.date)
        channel = _channel(order)
        counts[channel][month] += 1
        revenue[channel][month] += _order_revenue(order)
    rows = []
    for month in months:
        row: dict[str, str | dict] = {"month": month}
        for name in names:
            row[name] = {"orders": counts[name][month], "revenue": _money(revenue[name][month])}
        rows.append(row)
    return rows


def _overview_payments(orders: list[CrmOrder]) -> list[dict]:
    grouped: dict[str, list[CrmOrder]] = defaultdict(list)
    for order in orders:
        grouped[order.payment_type].append(order)
    rows = [
        {"type": payment_type, "orders": len(items), "revenue": _revenue(items)}
        for payment_type, items in grouped.items()
    ]
    rows.sort(key=lambda row: (-row["revenue"], -row["orders"], row["type"]))
    return [
        {"type": row["type"], "orders": row["orders"], "revenue": _money(row["revenue"])} for row in rows
    ]


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


def nickname_key(value: str) -> str:
    normalized = re.sub(r"[^a-zа-я0-9]+", "", value.lower().replace("ё", "е"))
    if normalized in _GENERIC_NAMES or len(normalized) < _NICKNAME_LENGTH:
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
    nick_phones: dict[str, set[str]] = defaultdict(set)
    phones_by_id: dict[int, list[str]] = {}
    nick_by_id: dict[int, str] = {}
    for order in orders:
        phones = order_phones(order)
        phones_by_id[order.id] = phones
        nick = nickname_key(order.nickname)
        nick_by_id[order.id] = nick
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
            if nick:
                nick_phones[nick].update(phones)
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
        if phones:
            key = "p:" + _find(parent, phones[0])
        else:
            nick = nick_by_id[order.id]
            if not nick:
                unknown += 1
                continue
            roots = {_find(parent, phone) for phone in nick_phones[nick]}
            if len(roots) == 1:
                key = "p:" + next(iter(roots))
            else:
                key = "n:" + nick
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


def _repeat(customers: dict[str, Customer]) -> list[Customer]:
    return [customer for customer in customers.values() if len(customer.orders) >= 2]


def _top_revenue(customers: dict[str, Customer]) -> list[Customer]:
    return sorted(
        _repeat(customers),
        key=lambda customer: (_revenue(customer.orders), len(customer.orders), customer.key),
        reverse=True,
    )[:_TOP_LIMIT]


def _top_orders(customers: dict[str, Customer]) -> list[Customer]:
    return sorted(
        _repeat(customers),
        key=lambda customer: (len(customer.orders), _revenue(customer.orders), customer.key),
        reverse=True,
    )[:_TOP_LIMIT]


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


def products(month: str, today: date) -> dict:
    start, end = windows(month, today)[:2]
    orders = list(
        CrmOrder.objects.filter(deleted=False, date__gte=start, date__lte=end).order_by("date", "id")
    )
    compositions = {
        composition.order_id: composition
        for composition in AnalyticsOrderComposition.objects.filter(order__in=orders).prefetch_related("items")
    }
    kinds: dict[str, _Count] = {}
    positions: dict[tuple[str, str], _Count] = {}
    fillings: dict[str, _Count] = {}
    weights: dict[Decimal, _Count] = {}
    weight_unknown = 0
    parsed = 0
    for order in orders:
        composition = compositions.get(order.id)
        if composition is None:
            continue
        parsed += 1
        for item in composition.items.all():
            kilograms = None if item.weight_kg is None else item.weight_kg * item.quantity
            _bump(kinds, item.kind, order.id, item.quantity, kilograms)
            _bump(positions, (item.kind, item.name), order.id, item.quantity, kilograms)
            if item.filling:
                _bump(fillings, item.filling, order.id, item.quantity, kilograms)
            if item.weight_kg is None:
                weight_unknown += item.quantity
            else:
                _bump(weights, item.weight_kg, order.id, item.quantity, kilograms)
    return {
        "month": month,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "coverage": {"orders": len(orders), "parsed": parsed},
        "kinds": [
            {"kind": kind, **_metrics(bucket)}
            for kind, bucket in sorted(kinds.items(), key=lambda item: (-item[1].quantity, item[0]))
        ],
        "positions": [
            {"kind": kind, "name": name, **_metrics(bucket)}
            for (kind, name), bucket in sorted(
                positions.items(), key=lambda item: (-item[1].quantity, item[0][1], item[0][0])
            )
        ],
        "fillings": [
            {"filling": filling, **_metrics(bucket)}
            for filling, bucket in sorted(fillings.items(), key=lambda item: (-item[1].quantity, item[0]))
        ],
        "weights": [
            {"kg": _num(kg), **_metrics(bucket)}
            for kg, bucket in sorted(weights.items(), key=lambda item: item[0])
        ],
        "weight_unknown": weight_unknown,
    }


class _Count:
    def __init__(self) -> None:
        self.quantity = 0
        self.order_ids: set[int] = set()
        self.kilograms = Decimal("0")


def _bump(buckets: dict, key, order_id: int, quantity: int, kilograms: Decimal | None) -> None:
    bucket = buckets.get(key)
    if bucket is None:
        bucket = _Count()
        buckets[key] = bucket
    bucket.quantity += quantity
    bucket.order_ids.add(order_id)
    if kilograms is not None:
        bucket.kilograms += kilograms


def _metrics(bucket: _Count) -> dict:
    return {
        "quantity": bucket.quantity,
        "orders": len(bucket.order_ids),
        "kilograms": _num(bucket.kilograms),
    }


_PRODUCTION_END = frozenset(
    {
        CrmOrder.STATUS_READY,
        CrmOrder.STATUS_CLIENT_APPROVED,
        CrmOrder.STATUS_IN_DELIVERY,
        CrmOrder.STATUS_DELIVERED,
    }
)


def _month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def _month_keys(start: date, end: date) -> list[str]:
    year = start.year
    month = start.month
    keys = []
    while (year, month) <= (end.year, end.month):
        keys.append(f"{year:04d}-{month:02d}")
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return keys


def _share(part: Decimal, whole: Decimal) -> str | None:
    if whole == 0:
        return None
    return _num(part / whole)


def _per_kg(money: Decimal, kilograms: Decimal) -> str | None:
    if kilograms == 0:
        return None
    return _money(money / kilograms)


def _per_hour(kilograms: Decimal, hours: Decimal) -> str | None:
    if hours == 0:
        return None
    return _num(kilograms / hours)


def _clock(stamps: list[datetime]) -> str | None:
    if not stamps:
        return None
    minutes = [stamp.astimezone(_TB).hour * 60 + stamp.astimezone(_TB).minute for stamp in stamps]
    total = int(Decimal(str(median(minutes))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"{total // 60:02d}:{total % 60:02d}"


def _shift_is_open(events: list[AttendanceEvent]) -> bool:
    collapsed: list[AttendanceEvent] = []
    for event in sorted(events, key=lambda item: item.timestamp):
        if not collapsed:
            collapsed.append(event)
            continue
        if collapsed[-1].event_type == event.event_type:
            if event.event_type == AttendanceEvent.DEPARTURE:
                collapsed[-1] = event
            continue
        collapsed.append(event)
    index = 0
    open_shift = False
    while index < len(collapsed):
        if collapsed[index].event_type == AttendanceEvent.DEPARTURE:
            index += 1
            continue
        if (
            index + 1 < len(collapsed)
            and collapsed[index + 1].event_type == AttendanceEvent.DEPARTURE
        ):
            index += 2
            continue
        open_shift = True
        index += 1
    return open_shift


def _staff_days(
    events: list[AttendanceEvent],
    hourly_rate: Decimal,
    monthly_rate: Decimal,
    start: date,
    end: date,
    today: date,
    open_now: datetime | None,
) -> dict[date, dict]:
    by_date: dict[date, list[AttendanceEvent]] = defaultdict(list)
    for event in events:
        by_date[event.timestamp.astimezone(_TB).date()].append(event)
    rows = {}
    current = start
    while current <= end:
        day_events = by_date.get(current, [])
        seconds = compute_day_worked_seconds(day_events, open_now if current == today else None)
        hours = (Decimal(seconds) / Decimal(3600)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if monthly_rate > 0:
            money = daily_monthly_share(monthly_rate, current)
        else:
            money = (Decimal(seconds) * hourly_rate / Decimal(3600)).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        arrivals = [event for event in day_events if event.event_type == AttendanceEvent.ARRIVAL]
        departures = [event for event in day_events if event.event_type == AttendanceEvent.DEPARTURE]
        closed = bool(arrivals) and bool(departures) and not _shift_is_open(day_events)
        rows[current] = {
            "hours": hours,
            "money": money,
            "unclosed": current < today and _shift_is_open(day_events),
            "arrival": min(event.timestamp for event in arrivals) if closed else None,
            "departure": max(event.timestamp for event in departures) if closed else None,
        }
        current += timedelta(days=1)
    return rows


def _walk(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _production_minutes(events: list[CrmOrderEvent]) -> Decimal | None:
    started = None
    for event in events:
        change = event.changes.get("status")
        if not isinstance(change, dict):
            continue
        new = change.get("new")
        if started is None:
            if new == CrmOrder.STATUS_IN_WORK:
                started = event.created_at
            continue
        if new in _PRODUCTION_END and started is not None:
            delta = event.created_at - started
            return Decimal(delta.days * 86400 + delta.seconds) / Decimal(60)
    return None


def _baker_rows(buckets: dict[int, dict], names: dict[int, str]) -> list[dict]:
    rows = []
    for user_id, bucket in buckets.items():
        if bucket["orders"] == 0 and bucket["kilograms"] == 0:
            continue
        rows.append(
            {
                "id": user_id,
                "name": names[user_id],
                "orders": bucket["orders"],
                "kilograms": bucket["kilograms"],
            }
        )
    rows.sort(key=lambda row: (-row["kilograms"], -row["orders"], row["name"].casefold(), row["id"]))
    return rows


def _format_bakers(rows: list[dict]) -> list[dict]:
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "kilograms": _num(row["kilograms"]),
            "orders": row["orders"],
        }
        for row in rows
    ]


def _touch_baker(buckets: dict[int, dict], user_id: int) -> dict:
    bucket = buckets.get(user_id)
    if bucket is None:
        bucket = {"orders": 0, "kilograms": Decimal("0")}
        buckets[user_id] = bucket
    return bucket


class _StaffPeriod:
    def __init__(self) -> None:
        self.hourly_money = Decimal("0")
        self.monthly_money = Decimal("0")
        self.hours = Decimal("0")
        self.shifts = 0
        self.revenue = Decimal("0")
        self.kilograms = Decimal("0")
        self.bakers: dict[int, dict] = {}
        self.unassigned_kilograms = Decimal("0")
        self.without_baker = 0
        self.orders = 0


def _collect_period(
    user_days: dict[int, dict[date, dict]],
    monthly_ids: set[int],
    orders_by_date: dict[date, list[CrmOrder]],
    start: date,
    end: date,
) -> _StaffPeriod:
    period = _StaffPeriod()
    for day in _walk(start, end):
        for user_id, days in user_days.items():
            row = days.get(day)
            if row is None:
                continue
            if user_id in monthly_ids:
                period.monthly_money += row["money"]
            else:
                period.hourly_money += row["money"]
            period.hours += row["hours"]
            if row["hours"] > 0:
                period.shifts += 1
        for order in orders_by_date.get(day, []):
            period.orders += 1
            period.revenue += _order_revenue(order)
            parsed = weight_kg(order.weight)
            kilograms = Decimal("0") if parsed is None else parsed
            period.kilograms += kilograms
            if order.taken_by_id is None:
                period.without_baker += 1
                period.unassigned_kilograms += kilograms
            else:
                bucket = _touch_baker(period.bakers, order.taken_by_id)
                bucket["orders"] += 1
                bucket["kilograms"] += kilograms
    return period


def _format_period(period: _StaffPeriod) -> dict:
    money = period.hourly_money + period.monthly_money
    return {
        "hourly_money": _money(period.hourly_money),
        "monthly_money": _money(period.monthly_money),
        "money": _money(money),
        "revenue": _money(period.revenue),
        "kilograms": _num(period.kilograms),
        "hours": _money(period.hours),
        "shifts": period.shifts,
        "salary_share": _share(money, period.revenue),
        "money_per_kg": _per_kg(money, period.kilograms),
        "kg_per_hour": _per_hour(period.kilograms, period.hours),
    }


def employees(month: str, today: date) -> dict:
    start, end, prev_start, prev_end = windows(month, today)
    now = timezone.now()
    open_now = now if now.astimezone(_TB).date() == today else None
    orders = list(
        CrmOrder.objects.filter(deleted=False).select_related("taken_by").order_by("date", "id")
    )
    events = list(AttendanceEvent.objects.select_related("user").order_by("timestamp", "id"))
    users: dict[int, User] = {}
    events_by_user: dict[int, list[AttendanceEvent]] = defaultdict(list)
    for event in events:
        users[event.user_id] = event.user
        events_by_user[event.user_id].append(event)
    for order in orders:
        if order.taken_by_id is not None:
            users[order.taken_by_id] = order.taken_by
    profiles = {
        profile.user_id: profile
        for profile in UserProfile.objects.filter(user_id__in=users).select_related("user")
    }
    for profile in UserProfile.objects.filter(monthly_rate__gt=0).select_related("user"):
        users[profile.user_id] = profile.user
        profiles[profile.user_id] = profile
    names = {user_id: chef_identity(user)[0] for user_id, user in users.items()}
    monthly_ids = {user_id for user_id, profile in profiles.items() if profile.monthly_rate > 0}
    firsts = []
    if orders:
        firsts.append(orders[0].date)
    if events:
        firsts.append(events[0].timestamp.astimezone(_TB).date())
    span_start = None if not firsts else date(min(firsts).year, min(firsts).month, 1)
    salary_start = prev_start if span_start is None else min(span_start, prev_start)
    salary_end = today if end <= today else end
    user_days = {
        user_id: _staff_days(
            events_by_user.get(user_id, []),
            profiles[user_id].hourly_rate if user_id in profiles else Decimal("0.00"),
            profiles[user_id].monthly_rate if user_id in profiles else Decimal("0.00"),
            salary_start,
            salary_end,
            today,
            open_now,
        )
        for user_id in users
    }
    orders_by_date: dict[date, list[CrmOrder]] = defaultdict(list)
    for order in orders:
        orders_by_date[order.date].append(order)
    selected = _collect_period(user_days, monthly_ids, orders_by_date, start, end)
    previous = _collect_period(user_days, monthly_ids, orders_by_date, prev_start, prev_end)
    window_orders = [order for order in orders if start <= order.date <= end]
    window_ids = [order.id for order in window_orders]
    compositions = {
        composition.order_id: composition
        for composition in AnalyticsOrderComposition.objects.filter(order_id__in=window_ids).prefetch_related(
            "items"
        )
    }
    status_events: dict[int, list[CrmOrderEvent]] = defaultdict(list)
    for event in CrmOrderEvent.objects.filter(order_id__in=window_ids).order_by("created_at", "id"):
        status_events[event.order_id].append(event)
    kinds_by_user: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    minutes_by_user: dict[int, list[Decimal]] = defaultdict(list)
    without_composition = 0
    without_production = 0
    for order in window_orders:
        composition = compositions.get(order.id)
        if composition is None:
            without_composition += 1
        elif order.taken_by_id is not None:
            for item in composition.items.all():
                kinds_by_user[order.taken_by_id][item.kind] += item.quantity
        if order.taken_by_id is None:
            continue
        minutes = _production_minutes(status_events.get(order.id, []))
        if minutes is None:
            without_production += 1
        else:
            minutes_by_user[order.taken_by_id].append(minutes)
    made_by_user = {
        user_id: bucket
        for user_id, bucket in selected.bakers.items()
    }
    people = []
    for user_id, days in user_days.items():
        hours = Decimal("0")
        money = Decimal("0")
        shifts = 0
        arrivals = []
        departures = []
        sheet = []
        unclosed = 0
        for day in _walk(start, end):
            row = days[day]
            hours += row["hours"]
            money += row["money"]
            if row["hours"] > 0:
                shifts += 1
            if row["unclosed"]:
                unclosed += 1
            if row["arrival"] is not None and row["departure"] is not None:
                arrivals.append(row["arrival"])
                departures.append(row["departure"])
            sheet.append(
                {
                    "date": day.isoformat(),
                    "hours": _money(row["hours"]),
                    "open": row["unclosed"],
                }
            )
        made = made_by_user.get(user_id, {"orders": 0, "kilograms": Decimal("0")})
        if hours == 0 and money == 0 and made["orders"] == 0 and unclosed == 0:
            continue
        kind_rows = [
            {"kind": kind, "quantity": quantity}
            for kind, quantity in sorted(kinds_by_user.get(user_id, {}).items(), key=lambda item: (-item[1], item[0]))
        ]
        samples = minutes_by_user.get(user_id, [])
        people.append(
            {
                "id": user_id,
                "name": names[user_id],
                "monthly": user_id in monthly_ids,
                "shifts": shifts,
                "hours": hours,
                "average_shift": None if shifts == 0 else hours / shifts,
                "money": money,
                "made": made["orders"],
                "made_kilograms": made["kilograms"],
                "arrival": _clock(arrivals),
                "departure": _clock(departures),
                "kinds": kind_rows,
                "production_minutes": None if not samples else Decimal(str(median(samples))),
                "production_orders": len(samples),
                "sheet": sheet,
                "unclosed": unclosed,
            }
        )
    people.sort(
        key=lambda row: (-row["money"], -row["made_kilograms"], row["name"].casefold(), row["id"])
    )
    fund = selected.hourly_money + selected.monthly_money
    days = []
    weekday_hours: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    weekday_kg: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    weekday_count: dict[int, int] = defaultdict(int)
    for day in _walk(start, end):
        day_hours = Decimal("0")
        for days_of_user in user_days.values():
            day_hours += days_of_user[day]["hours"]
        day_bakers: dict[int, dict] = {}
        unassigned = Decimal("0")
        day_kg = Decimal("0")
        for order in orders_by_date.get(day, []):
            parsed = weight_kg(order.weight)
            kilograms = Decimal("0") if parsed is None else parsed
            day_kg += kilograms
            if order.taken_by_id is None:
                unassigned += kilograms
            else:
                bucket = _touch_baker(day_bakers, order.taken_by_id)
                bucket["orders"] += 1
                bucket["kilograms"] += kilograms
        days.append(
            {
                "date": day.isoformat(),
                "hours": _money(day_hours),
                "kilograms": _num(day_kg),
                "kg_per_hour": _per_hour(day_kg, day_hours),
                "bakers": [
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "kilograms": _num(row["kilograms"]),
                    }
                    for row in _baker_rows(day_bakers, names)
                    if row["kilograms"] > 0
                ],
                "unassigned_kilograms": _num(unassigned),
            }
        )
        weekday = day.weekday()
        weekday_hours[weekday] += day_hours
        weekday_kg[weekday] += day_kg
        weekday_count[weekday] += 1
    months = []
    if span_start is not None:
        for key in _month_keys(span_start, today):
            month_start, month_last = _month_bounds(key)
            partial = _month_key(today) == key
            month_end = today if partial else month_last
            period = _collect_period(user_days, monthly_ids, orders_by_date, month_start, month_end)
            payload = _format_period(period)
            months.append(
                {
                    "month": key,
                    "partial": partial,
                    "hourly_money": payload["hourly_money"],
                    "monthly_money": payload["monthly_money"],
                    "revenue": payload["revenue"],
                    "kilograms": payload["kilograms"],
                    "hours": payload["hours"],
                    "salary_share": payload["salary_share"],
                    "money_per_kg": payload["money_per_kg"],
                    "kg_per_hour": payload["kg_per_hour"],
                    "bakers": _format_bakers(_baker_rows(period.bakers, names)),
                    "unassigned_kilograms": _num(period.unassigned_kilograms),
                }
            )
    return {
        "month": month,
        "totals": _format_period(selected),
        "previous": _format_period(previous),
        "gaps": {
            "without_baker": selected.without_baker,
            "unclosed_shifts": sum(row["unclosed"] for row in people),
            "without_composition": without_composition,
            "without_production": without_production,
        },
        "months": months,
        "days": days,
        "weekdays": [
            {
                "weekday": weekday,
                "hours": _money(weekday_hours[weekday] / Decimal(weekday_count[weekday])),
                "kilograms": _num(weekday_kg[weekday] / Decimal(weekday_count[weekday])),
            }
            for weekday in range(7)
            if weekday_count[weekday] > 0
        ],
        "employees": [
            {
                "id": row["id"],
                "name": row["name"],
                "monthly": row["monthly"],
                "shifts": row["shifts"],
                "hours": _money(row["hours"]),
                "average_shift": None if row["average_shift"] is None else _money(row["average_shift"]),
                "money": _money(row["money"]),
                "money_share": _share(row["money"], fund),
                "made": row["made"],
                "made_kilograms": _num(row["made_kilograms"]),
                "arrival": row["arrival"],
                "departure": row["departure"],
                "kinds": row["kinds"],
                "production_minutes": None
                if row["production_minutes"] is None
                else _num(row["production_minutes"]),
                "production_orders": row["production_orders"],
            }
            for row in people
        ],
        "timesheet": [
            {"id": row["id"], "name": row["name"], "days": row["sheet"]}
            for row in people
        ],
    }


def _group_revenue(customers: list[Customer]) -> Decimal:
    total = Decimal("0")
    for customer in customers:
        total += _revenue(customer.orders)
    return total
