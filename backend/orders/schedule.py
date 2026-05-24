from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from django.utils.translation import gettext_lazy as _
from django.utils import timezone as django_timezone
from rest_framework import serializers

from cart.models import Cart
from catalog.models import Product


CUTOFF_HOUR = 15
SLOT_START_HOUR = 11
SCHEDULE_LAST_HOUR = 20
EXPRESS_HOURS = 2
SCHEDULE_MAX_DAYS_AHEAD = 60
TIMEZONE_LABEL = "Asia/Tbilisi"
_TB = ZoneInfo(TIMEZONE_LABEL)

TIER_SAME_DAY = Product.DELIVERY_SCHEDULE_SAME_DAY
TIER_NEXT_DAY = Product.DELIVERY_SCHEDULE_NEXT_DAY
TIER_PLUS_2 = Product.DELIVERY_SCHEDULE_PLUS_2
TIER_PLUS_3 = Product.DELIVERY_SCHEDULE_PLUS_3

_DELIVERY_RANK: dict[str, int] = {
    TIER_SAME_DAY: 0,
    TIER_NEXT_DAY: 1,
    TIER_PLUS_2: 2,
    TIER_PLUS_3: 3,
}

ScheduleMode = Literal["express", "slot"]


@dataclass(frozen=True)
class TimeSlotRepr:
    start_time: time
    end_time: time

    def as_api(self) -> dict[str, str]:
        def fmt(t: time) -> str:
            return f"{t.hour:02d}:{t.minute:02d}"

        return {"start_time": fmt(self.start_time), "end_time": fmt(self.end_time)}


def now_tb(now: datetime | None = None) -> datetime:
    if now is None:
        now = django_timezone.now()
    if now.tzinfo is None:
        now = django_timezone.make_aware(now, UTC)
    return now.astimezone(_TB)


def ceiling_to_hour(local_dt: datetime) -> datetime:
    base = local_dt.replace(minute=0, second=0, microsecond=0)
    if local_dt <= base:
        return base
    return base + timedelta(hours=1)


def cutoff_dt_on_date(local_date: date) -> datetime:
    return datetime.combine(local_date, time(CUTOFF_HOUR, 0), tzinfo=_TB)


_TIER_FROM_RANK: dict[int, str] = {v: k for k, v in _DELIVERY_RANK.items()}


def effective_tier_from_cart(cart: Cart) -> str:
    qs = cart.items.select_related("product__category").all()
    if not qs:
        raise serializers.ValidationError({"cart": _("Cart is empty.")})
    max_rank = 0
    for item in qs:
        tier = item.product.effective_delivery_schedule_tier
        r = _DELIVERY_RANK[tier]
        if r > max_rank:
            max_rank = r
    return _TIER_FROM_RANK[max_rank]


def _min_booking_date(tier: str, today_tb: date, local_now: datetime) -> date:
    if tier == TIER_SAME_DAY:
        if local_now < cutoff_dt_on_date(today_tb):
            return today_tb
        return today_tb + timedelta(days=1)
    if tier == TIER_NEXT_DAY:
        return today_tb + timedelta(days=1)
    if tier == TIER_PLUS_2:
        return today_tb + timedelta(days=2)
    if tier == TIER_PLUS_3:
        return today_tb + timedelta(days=3)
    raise serializers.ValidationError({"tier": _("Invalid schedule tier.")})


def hourly_slots_for_date(day: date, local_now: datetime) -> list[TimeSlotRepr]:
    today_d = local_now.date()
    if day < today_d:
        return []

    slots: list[TimeSlotRepr] = []
    if day == today_d:
        threshold = local_now + timedelta(hours=EXPRESS_HOURS)
        floor = ceiling_to_hour(threshold)
        if floor.date() != today_d:
            return []
        first_h = max(SLOT_START_HOUR, floor.hour)
    else:
        first_h = SLOT_START_HOUR

    for h in range(first_h, SCHEDULE_LAST_HOUR + 1):
        slots.append(TimeSlotRepr(start_time=time(h, 0), end_time=time(h + 1, 0)))

    return slots


def express_available_for_tier(tier: str, local_now: datetime) -> bool:
    if tier != TIER_SAME_DAY:
        return False
    today_d = local_now.date()
    if local_now >= cutoff_dt_on_date(today_d):
        return False
    work_start = datetime.combine(today_d, time(SLOT_START_HOUR, 0), tzinfo=_TB)
    if local_now < work_start:
        return False
    return True


def build_fulfillment_options(cart: Cart) -> dict:
    tier = effective_tier_from_cart(cart)
    local_now = now_tb()
    today_d = local_now.date()

    express_on = express_available_for_tier(tier, local_now)
    min_d = _min_booking_date(tier, today_d, local_now)

    date_entries: list[dict] = []
    for delta in range(0, SCHEDULE_MAX_DAYS_AHEAD + 1):
        target = min_d + timedelta(days=delta)
        slots_repr = hourly_slots_for_date(target, local_now)
        if not slots_repr:
            continue
        date_entries.append(
            {
                "date": target.isoformat(),
                "slots": [s.as_api() for s in slots_repr],
            }
        )

    return {
        "timezone": TIMEZONE_LABEL,
        "express_available": express_on,
        "dates": date_entries,
    }


def resolve_schedule_selection(
    cart: Cart,
    mode: ScheduleMode,
    slot_date: date | None,
    slot_start_time: time | None,
    slot_end_time: time | None,
) -> tuple[datetime, datetime]:
    opts = build_fulfillment_options(cart)
    if mode == "express":
        if not opts["express_available"]:
            raise serializers.ValidationError(
                {"schedule_mode": _("Express delivery is not available for this order.")}
            )
        nw = django_timezone.now()
        start = nw
        end = nw + timedelta(hours=EXPRESS_HOURS)
        return start, end

    if mode != "slot":
        raise serializers.ValidationError({"schedule_mode": _("Invalid schedule mode.")})

    if slot_date is None or slot_start_time is None or slot_end_time is None:
        raise serializers.ValidationError(
            {"schedule": _("Date and time window are required for scheduled delivery.")}
        )

    for entry in opts["dates"]:
        if entry["date"] != slot_date.isoformat():
            continue
        for s in entry["slots"]:
            if (
                s["start_time"] == _fmt_time(slot_start_time)
                and s["end_time"] == _fmt_time(slot_end_time)
            ):
                dt_start_local = datetime.combine(slot_date, slot_start_time, tzinfo=_TB)
                dt_end_local = datetime.combine(slot_date, slot_end_time, tzinfo=_TB)
                return dt_start_local.astimezone(UTC), dt_end_local.astimezone(UTC)

    raise serializers.ValidationError({"schedule": _("Selected time slot is not available.")})


def _fmt_time(t: time) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"
