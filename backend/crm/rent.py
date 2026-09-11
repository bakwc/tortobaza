from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from crm.models import CrmSettings


def monthly_rent() -> Decimal:
    return CrmSettings.load().monthly_rent


def daily_rent(target_date: date) -> Decimal:
    days = monthrange(target_date.year, target_date.month)[1]
    return (monthly_rent() / Decimal(days)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
