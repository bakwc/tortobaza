from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import UserProfile
from attendance.models import AttendanceEvent

User = get_user_model()

_TB = ZoneInfo("Asia/Tbilisi")


def compute_day_worked_seconds(events: list[AttendanceEvent]) -> int:
    sorted_events = sorted(events, key=lambda event: event.timestamp)
    collapsed: list[AttendanceEvent] = []
    for event in sorted_events:
        if not collapsed:
            collapsed.append(event)
            continue
        if collapsed[-1].event_type == event.event_type:
            if event.event_type == AttendanceEvent.DEPARTURE:
                collapsed[-1] = event
            continue
        collapsed.append(event)

    total_seconds = 0
    index = 0
    while index < len(collapsed):
        if collapsed[index].event_type == AttendanceEvent.DEPARTURE:
            index += 1
            continue
        if (
            index + 1 < len(collapsed)
            and collapsed[index + 1].event_type == AttendanceEvent.DEPARTURE
        ):
            delta = collapsed[index + 1].timestamp - collapsed[index].timestamp
            total_seconds += int(delta.total_seconds())
            index += 2
            continue
        index += 1

    return total_seconds


def compute_salary(user, start_date: date, end_date: date) -> dict:
    profile = UserProfile.objects.filter(user=user).first()
    hourly_rate = profile.hourly_rate if profile else Decimal("0.00")

    start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()), _TB)
    end_dt = timezone.make_aware(
        datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
        _TB,
    )

    events = AttendanceEvent.objects.filter(
        user=user,
        timestamp__gte=start_dt,
        timestamp__lt=end_dt,
    ).order_by("timestamp")

    by_date: dict[date, list[AttendanceEvent]] = {}
    for event in events:
        local_date = event.timestamp.astimezone(_TB).date()
        by_date.setdefault(local_date, []).append(event)

    rows = []
    total_hours = Decimal("0.00")
    total_money = Decimal("0.00")
    current = start_date
    while current <= end_date:
        day_events = by_date.get(current, [])
        seconds = compute_day_worked_seconds(day_events)
        hours = (Decimal(seconds) / Decimal(3600)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        money = (Decimal(seconds) * hourly_rate / Decimal(3600)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        arrivals = [event for event in day_events if event.event_type == AttendanceEvent.ARRIVAL]
        departures = [
            event for event in day_events if event.event_type == AttendanceEvent.DEPARTURE
        ]
        first_arrival = min((event.timestamp for event in arrivals), default=None)
        last_departure = max((event.timestamp for event in departures), default=None)
        rows.append(
            {
                "date": current,
                "arrival": first_arrival,
                "departure": last_departure,
                "hours": hours,
                "money": money,
            }
        )
        total_hours += hours
        total_money += money
        current += timedelta(days=1)

    return {
        "hourly_rate": hourly_rate,
        "rows": rows,
        "total_hours": total_hours,
        "total_money": total_money,
    }


def compute_all_salaries(start_date: date, end_date: date) -> dict:
    start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()), _TB)
    end_dt = timezone.make_aware(
        datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
        _TB,
    )
    user_ids = (
        AttendanceEvent.objects.filter(
            timestamp__gte=start_dt,
            timestamp__lt=end_dt,
        )
        .values_list("user_id", flat=True)
        .distinct()
    )
    users = User.objects.filter(id__in=user_ids)
    total_money = Decimal("0.00")
    by_date: dict[date, Decimal] = {}
    for user in users:
        result = compute_salary(user, start_date, end_date)
        total_money += result["total_money"]
        for row in result["rows"]:
            day = row["date"]
            by_date[day] = by_date.get(day, Decimal("0.00")) + row["money"]
    return {
        "total_money": total_money,
        "by_date": by_date,
    }
