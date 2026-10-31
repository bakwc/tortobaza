import random
import time
from datetime import timedelta
from decimal import Decimal

import requests
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from crm.models import ExchangeRateSnapshot

NBG_CURRENCIES_URL = "https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/"
NBG_TIMEOUT_SECONDS = 10
CACHE_TTL = timedelta(hours=24)
ATTEMPTS = 5


def _snapshot_from_response(response: requests.Response) -> ExchangeRateSnapshot:
    response.raise_for_status()
    entry = response.json()[0]
    rates = {}
    for currency in entry["currencies"]:
        per_unit = Decimal(str(currency["rate"])) / Decimal(str(currency["quantity"]))
        rates[currency["code"]] = str(per_unit)
    return ExchangeRateSnapshot.objects.create(
        rates_date=parse_datetime(entry["date"]).date(),
        rates=rates,
    )


def _cached_usd_rate() -> Decimal | None:
    latest = ExchangeRateSnapshot.objects.order_by("-fetched_at", "-pk").first()
    if latest is None or "USD" not in latest.rates:
        return None
    return Decimal(latest.rates["USD"])


def usd_rate() -> Decimal:
    attempt = 0
    while True:
        try:
            response = requests.get(NBG_CURRENCIES_URL, timeout=NBG_TIMEOUT_SECONDS)
            snapshot = _snapshot_from_response(response)
            return Decimal(snapshot.rates["USD"])
        except (requests.ConnectionError, requests.Timeout):
            cached = _cached_usd_rate()
            if cached is not None:
                return cached
            attempt += 1
            if attempt == ATTEMPTS:
                raise
            time.sleep(random.uniform(1, 2))


def current_exchange_rates() -> ExchangeRateSnapshot:
    latest = ExchangeRateSnapshot.objects.order_by("-fetched_at", "-pk").first()
    if latest is not None and timezone.now() - latest.fetched_at < CACHE_TTL:
        return latest
    try:
        response = requests.get(NBG_CURRENCIES_URL, timeout=NBG_TIMEOUT_SECONDS)
        return _snapshot_from_response(response)
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError, AttributeError):
        if latest is None:
            raise
        return latest
