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


def _presence_rank(row: dict) -> int:
    if row["on_site"]:
        return 0
    if row["departure"] is not None:
        return 1
    return 2


def today_overview(today: date, tomorrow: date) -> dict:
    users = list(_schedule_users())
    work_rows = ScheduleDay.objects.filter(
        user__in=users,
        date__in=[today, tomorrow],
        day_type=ScheduleDay.WORK,
    )
    scheduled_today = {row.user_id for row in work_rows if row.date == today}
    scheduled_tomorrow = {row.user_id for row in work_rows if row.date == tomorrow}
    start_dt = timezone.make_aware(datetime.combine(today, datetime.min.time()), _TB)
    end_dt = timezone.make_aware(datetime.combine(today + timedelta(days=1), datetime.min.time()), _TB)
    events = AttendanceEvent.objects.filter(
        user__in=users,
        timestamp__gte=start_dt,
        timestamp__lt=end_dt,
    ).order_by("timestamp")
    events_by_user: dict[int, list[AttendanceEvent]] = {}
    for event in events:
        events_by_user.setdefault(event.user_id, []).append(event)
    by_id = {row["id"]: row for row in _employee_rows(users)}
    today_employees = []
    for user in users:
        day_events = events_by_user.get(user.id, [])
        scheduled = user.id in scheduled_today
        if not scheduled and not day_events:
            continue
        on_site = bool(day_events) and day_events[-1].event_type == AttendanceEvent.ARRIVAL
        today_employees.append(
            {
                "id": user.id,
                "name": by_id[user.id]["name"],
                "position": by_id[user.id]["position"],
                "scheduled": scheduled,
                "on_site": on_site,
                "arrival": _clock(day_events, AttendanceEvent.ARRIVAL),
                "departure": None if on_site else _clock(day_events, AttendanceEvent.DEPARTURE),
            }
        )
    today_employees.sort(key=lambda row: (_presence_rank(row), row["name"].casefold(), row["id"]))
    tomorrow_employees = [
        {
            "id": user.id,
            "name": by_id[user.id]["name"],
            "position": by_id[user.id]["position"],
        }
        for user in users
        if user.id in scheduled_tomorrow
    ]
    tomorrow_employees.sort(key=lambda row: (row["name"].casefold(), row["id"]))
    return {
        "today": today.isoformat(),
        "tomorrow": tomorrow.isoformat(),
        "today_employees": today_employees,
        "tomorrow_employees": tomorrow_employees,
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


def _clock(events: list[AttendanceEvent], event_type: str) -> str | None:
    stamps = [event.timestamp for event in events if event.event_type == event_type]
    if event_type == AttendanceEvent.ARRIVAL:
        moment = min(stamps, default=None)
    else:
        moment = max(stamps, default=None)
    if moment is None:
        return None
    return moment.astimezone(_TB).strftime("%H:%M")


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
            day_events = events_by_key.get((user.id, day), [])
            seconds = compute_day_worked_seconds(day_events, None)
            hours = _hours(seconds)
            day_type = types_by_key.get((user.id, day))
            days_by_user[user.id][day.isoformat()] = {
                "day_type": day_type,
                "hours": str(hours),
                "mismatch": _mismatch(day_type, hours, day, today),
                "arrival": _clock(day_events, AttendanceEvent.ARRIVAL),
                "departure": _clock(day_events, AttendanceEvent.DEPARTURE),
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
