from datetime import date, timedelta
from unittest.mock import Mock, patch

import requests
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from crm.exchange_rates import NBG_CURRENCIES_URL, current_exchange_rates
from crm.models import ExchangeRateSnapshot

NBG_PAYLOAD = [
    {
        "date": "2026-10-10T00:00:00.000Z",
        "currencies": [
            {"code": "USD", "quantity": 1, "rate": 2.6005},
            {"code": "EUR", "quantity": 1, "rate": 3.0451},
        ],
    }
]


def _response() -> Mock:
    response = Mock()
    response.json.return_value = NBG_PAYLOAD
    return response


def _snapshot(hours_ago: int) -> ExchangeRateSnapshot:
    snapshot = ExchangeRateSnapshot.objects.create(
        rates_date=date(2026, 10, 9),
        rates={"USD": "2.5900"},
    )
    ExchangeRateSnapshot.objects.filter(pk=snapshot.pk).update(
        fetched_at=timezone.now() - timedelta(hours=hours_ago)
    )
    snapshot.refresh_from_db()
    return snapshot


class CurrentExchangeRatesTests(TestCase):
    def test_fresh_cache_skips_http(self):
        snapshot = _snapshot(1)
        with patch("crm.exchange_rates.requests.get") as get:
            result = current_exchange_rates()
        get.assert_not_called()
        self.assertEqual(result.pk, snapshot.pk)

    def test_stale_cache_fetches_and_stores(self):
        old = _snapshot(25)
        with patch("crm.exchange_rates.requests.get", return_value=_response()) as get:
            result = current_exchange_rates()
        get.assert_called_once_with(NBG_CURRENCIES_URL, timeout=10)
        self.assertNotEqual(result.pk, old.pk)
        self.assertEqual(result.rates_date, date(2026, 10, 10))
        self.assertEqual(result.rates, {"USD": "2.6005", "EUR": "3.0451"})
        self.assertEqual(ExchangeRateSnapshot.objects.count(), 2)

    def test_failed_fetch_returns_older_snapshot(self):
        old = _snapshot(25)
        with patch(
            "crm.exchange_rates.requests.get",
            side_effect=requests.RequestException("down"),
        ):
            result = current_exchange_rates()
        self.assertEqual(result.pk, old.pk)
        self.assertEqual(ExchangeRateSnapshot.objects.count(), 1)


class ExchangeRatesApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username="admin", password="password", is_staff=True)
        UserProfile.objects.create(user=self.admin, is_finance_admin=True)

    def test_returns_latest_snapshot(self):
        _snapshot(1)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/crm/finance/exchange-rates/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"date": "2026-10-09", "rates": {"USD": "2.5900"}},
        )
