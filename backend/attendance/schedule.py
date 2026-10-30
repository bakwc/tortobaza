from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import chef_identity
from attendance.models import AttendanceEvent, ScheduleDay
from attendance.salary import compute_day_worked_seconds

User = get_user_model()

_TB = ZoneInfo("Asia/Tbilisi")


def month_bounds(month: str) -> tuple[date, date]:
    year_text, month_text = month.split("-")
    year = int(year_text)
    month_number = int(month_text)
    last_day = monthrange(year, month_number)[1]
    return date(year, month_number, 1), date(year, month_number, last_day)


def _daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _schedule_users():
    return User.objects.filter(is_active=True, profile__in_schedule=True).select_related("profile")


def _employee_rows(users) -> list[dict]:
    rows = []
    for user in users:
        name = chef_identity(user)[0]
        rows.append(
            {
                "id": user.id,
                "name": name,
                "position": user.profile.position,
            }
        )
    rows.sort(key=lambda row: (row["name"].casefold(), row["id"]))
    return rows


def schedule_grid(start: date, end: date) -> dict:
    users = list(_schedule_users())
    days_by_user: dict[int, dict[str, str]] = {user.id: {} for user in users}
    scheduled = ScheduleDay.objects.filter(user__in=users, date__gte=start, date__lte=end)
    for row in scheduled:
        days_by_user[row.user_id][row.date.isoformat()] = row.day_type
    employees = _employee_rows(users)
    for employee in employees:
        employee["days"] = days_by_user[employee["id"]]
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "employees": employees,
    }


def save_cells(cells: list[dict]) -> None:
    for cell in cells:
        if cell["day_type"] is None:
            ScheduleDay.objects.filter(user_id=cell["user"], date=cell["date"]).delete()
            continue
        ScheduleDay.objects.update_or_create(
            user_id=cell["user"],
            date=cell["date"],
            defaults={"day_type": cell["day_type"]},
        )


def apply_pattern(user, start: date, end: date, cycle_start: date, pattern: list[str]) -> None:
    length = len(pattern)
    for day in _daterange(start, end):
        index = (day - cycle_start).days % length
        ScheduleDay.objects.update_or_create(
            user=user,
            date=day,
            defaults={"day_type": pattern[index]},
        )


def _hours(seconds: int) -> Decimal:
    return (Decimal(seconds) / Decimal(3600)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _mismatch(day_type: str | None, hours: Decimal, day: date, today: date) -> bool:
    if hours > 0 and day_type != ScheduleDay.WORK:
        return True
    if hours == 0 and day_type == ScheduleDay.WORK and day < today:
        return True
    return False


def timesheet_grid(start: date, end: date, today: date) -> dict:
    users = list(_schedule_users())
    start_dt = timezone.make_aware(datetime.combine(start, datetime.min.time()), _TB)
    end_dt = timezone.make_aware(datetime.combine(end + timedelta(days=1), datetime.min.time()), _TB)
    events = AttendanceEvent.objects.filter(
        user__in=users,
        timestamp__gte=start_dt,
        timestamp__lt=end_dt,
    ).order_by("timestamp")
    events_by_key: dict[tuple[int, date], list[AttendanceEvent]] = {}
    for event in events:
        local_date = event.timestamp.astimezone(_TB).date()
        events_by_key.setdefault((event.user_id, local_date), []).append(event)
    types_by_key = {
        (row.user_id, row.date): row.day_type
        for row in ScheduleDay.objects.filter(user__in=users, date__gte=start, date__lte=end)
    }
    days_by_user: dict[int, dict[str, dict]] = {user.id: {} for user in users}
    totals: dict[int, Decimal] = {user.id: Decimal("0.00") for user in users}
    for user in users:
        for day in _daterange(start, end):
            seconds = compute_day_worked_seconds(events_by_key.get((user.id, day), []), None)
            hours = _hours(seconds)
            day_type = types_by_key.get((user.id, day))
            days_by_user[user.id][day.isoformat()] = {
                "day_type": day_type,
                "hours": str(hours),
                "mismatch": _mismatch(day_type, hours, day, today),
            }
            totals[user.id] += hours
    employees = _employee_rows(users)
    for employee in employees:
        employee["days"] = days_by_user[employee["id"]]
        employee["total_hours"] = str(totals[employee["id"]])
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "employees": employees,
    }
