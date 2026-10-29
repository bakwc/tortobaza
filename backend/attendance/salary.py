from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import UserProfile, chef_identity
from attendance.models import AttendanceEvent

User = get_user_model()

_TB = ZoneInfo("Asia/Tbilisi")


def compute_day_worked_seconds(
    events: list[AttendanceEvent],
    open_until: datetime | None,
) -> int:
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
        if open_until is not None and open_until > collapsed[index].timestamp:
            delta = open_until - collapsed[index].timestamp
            total_seconds += int(delta.total_seconds())
        index += 1

    return total_seconds


def daily_monthly_share(monthly_rate: Decimal, day: date) -> Decimal:
    days = monthrange(day.year, day.month)[1]
    base = (monthly_rate / Decimal(days)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if day.day == days:
        return monthly_rate - base * (days - 1)
    return base


def compute_salary(
    user,
    start_date: date,
    end_date: date,
    open_until: datetime | None,
) -> dict:
    profile = UserProfile.objects.filter(user=user).first()
    hourly_rate = profile.hourly_rate if profile else Decimal("0.00")
    monthly_rate = profile.monthly_rate if profile else Decimal("0.00")

    start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()), _TB)
    end_dt = timezone.make_aware(
        datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
        _TB,
    )

    open_until_date = open_until.astimezone(_TB).date() if open_until is not None else None

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
        seconds = compute_day_worked_seconds(
            day_events,
            open_until if current == open_until_date else None,
        )
        hours = (Decimal(seconds) / Decimal(3600)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        if monthly_rate > 0:
            money = daily_monthly_share(monthly_rate, current)
        else:
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
        "monthly": monthly_rate > 0,
        "rows": rows,
        "total_hours": total_hours,
        "total_money": total_money,
    }


def _salary_users(start_date: date, end_date: date):
    start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()), _TB)
    end_dt = timezone.make_aware(
        datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
        _TB,
    )
    event_user_ids = AttendanceEvent.objects.filter(
        timestamp__gte=start_dt,
        timestamp__lt=end_dt,
    ).values_list("user_id", flat=True)
    monthly_user_ids = UserProfile.objects.filter(monthly_rate__gt=0).values_list(
        "user_id",
        flat=True,
    )
    user_ids = set(event_user_ids) | set(monthly_user_ids)
    return User.objects.filter(id__in=user_ids)


def _employee_sort_key(row: dict) -> tuple[str, int]:
    return (row["name"].casefold(), row["id"])


def compute_all_salaries(start_date: date, end_date: date) -> dict:
    users = _salary_users(start_date, end_date)
    total_money = Decimal("0.00")
    by_date: dict[date, Decimal] = {}
    employees: list[dict] = []
    employees_by_date: dict[date, list[dict]] = {}
    for user in users:
        result = compute_salary(user, start_date, end_date, timezone.now())
        total_money += result["total_money"]
        name = chef_identity(user)[0]
        hours = Decimal("0.00")
        money = Decimal("0.00")
        for row in result["rows"]:
            day = row["date"]
            by_date[day] = by_date.get(day, Decimal("0.00")) + row["money"]
            hours += row["hours"]
            money += row["money"]
            if row["hours"] > 0 or row["money"] > 0:
                employees_by_date.setdefault(day, []).append(
                    {
                        "id": user.id,
                        "name": name,
                        "hours": row["hours"],
                        "money": row["money"],
                    }
                )
        if hours > 0 or money > 0:
            employees.append(
                {
                    "id": user.id,
                    "name": name,
                    "hours": hours,
                    "money": money,
                }
            )
    employees.sort(key=_employee_sort_key)
    for day_employees in employees_by_date.values():
        day_employees.sort(key=_employee_sort_key)
    return {
        "total_money": total_money,
        "by_date": by_date,
        "employees": employees,
        "employees_by_date": employees_by_date,
    }


def _period_totals(employees: list[dict]) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    hourly_hours = Decimal("0.00")
    hourly_money = Decimal("0.00")
    monthly_hours = Decimal("0.00")
    monthly_money = Decimal("0.00")
    for employee in employees:
        if employee["monthly"]:
            monthly_hours += employee["hours"]
            monthly_money += employee["money"]
        else:
            hourly_hours += employee["hours"]
            hourly_money += employee["money"]
    return hourly_hours, hourly_money, monthly_hours, monthly_money


def compute_month_salaries(year: int, month: int) -> dict:
    last_day = monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)
    first_end = date(year, month, 14)
    second_start = date(year, month, 15)
    users = _salary_users(start_date, end_date)
    first_employees: list[dict] = []
    second_employees: list[dict] = []
    for user in users:
        result = compute_salary(user, start_date, end_date, None)
        name = chef_identity(user)[0]
        first_hours = Decimal("0.00")
        first_money = Decimal("0.00")
        second_hours = Decimal("0.00")
        second_money = Decimal("0.00")
        for row in result["rows"]:
            if row["date"] <= first_end:
                first_hours += row["hours"]
                first_money += row["money"]
            else:
                second_hours += row["hours"]
                second_money += row["money"]
        if first_hours > 0 or first_money > 0:
            first_employees.append(
                {
                    "id": user.id,
                    "name": name,
                    "hours": first_hours,
                    "money": first_money,
                    "monthly": result["monthly"],
                }
            )
        if second_hours > 0 or second_money > 0:
            second_employees.append(
                {
                    "id": user.id,
                    "name": name,
                    "hours": second_hours,
                    "money": second_money,
                    "monthly": result["monthly"],
                }
            )
    first_employees.sort(key=lambda row: (row["name"].casefold(), row["id"]))
    second_employees.sort(key=lambda row: (row["name"].casefold(), row["id"]))
    first_hourly_hours, first_hourly_money, first_monthly_hours, first_monthly_money = _period_totals(
        first_employees
    )
    second_hourly_hours, second_hourly_money, second_monthly_hours, second_monthly_money = (
        _period_totals(second_employees)
    )
    return {
        "month": f"{year:04d}-{month:02d}",
        "periods": [
            {
                "start": start_date,
                "end": first_end,
                "employees": first_employees,
                "hourly_hours": first_hourly_hours,
                "hourly_money": first_hourly_money,
                "monthly_hours": first_monthly_hours,
                "monthly_money": first_monthly_money,
            },
            {
                "start": second_start,
                "end": end_date,
                "employees": second_employees,
                "hourly_hours": second_hourly_hours,
                "hourly_money": second_hourly_money,
                "monthly_hours": second_monthly_hours,
                "monthly_money": second_monthly_money,
            },
        ],
        "hourly_hours": first_hourly_hours + second_hourly_hours,
        "hourly_money": first_hourly_money + second_hourly_money,
        "monthly_hours": first_monthly_hours + second_monthly_hours,
        "monthly_money": first_monthly_money + second_monthly_money,
    }
