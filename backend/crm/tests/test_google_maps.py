from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from crm.google_maps import yandex_url_to_google_url
from crm.models import ResolvedGoogleAddress, ResolvedYandexAddress
from crm.yandex_maps import YANDEX_MAPS_PROMPT_ID, YANDEX_MAPS_PROMPT_VERSION

YANDEX_URL = "https://yandex.com/maps/?text=Rustaveli"
GOOGLE_URL = "https://www.google.com/maps/search/?api=1&query=41.623987,41.645449"
COORDINATES_HTML = '"coordinates":[41.645449,41.623987]'
COORDS_HTML = '"coords":[41.645449,41.623987]'
BRACKET_HTML = "[41.645449, 41.623987]"
OUTSIDE_GEORGIA_HTML = '"coordinates":[10.0,20.0]'


def _fake_get(text: str) -> MagicMock:
    response = MagicMock()
    response.text = text
    response.raise_for_status = MagicMock()
    return response


class YandexUrlToGoogleUrlTests(TestCase):
    @patch("crm.google_maps.requests.get")
    def test_coordinates_pattern(self, get):
        get.return_value = _fake_get(COORDINATES_HTML)
        self.assertEqual(yandex_url_to_google_url(YANDEX_URL), GOOGLE_URL)
        get.assert_called_once()

    @patch("crm.google_maps.requests.get")
    def test_coords_pattern(self, get):
        get.return_value = _fake_get(COORDS_HTML)
        self.assertEqual(yandex_url_to_google_url(YANDEX_URL), GOOGLE_URL)

    @patch("crm.google_maps.requests.get")
    def test_bracket_pattern(self, get):
        get.return_value = _fake_get(BRACKET_HTML)
        self.assertEqual(yandex_url_to_google_url(YANDEX_URL), GOOGLE_URL)

    @patch("crm.google_maps.requests.get")
    def test_rejects_coordinates_outside_georgia(self, get):
        get.return_value = _fake_get(OUTSIDE_GEORGIA_HTML)
        with self.assertRaises(ValueError):
            yandex_url_to_google_url(YANDEX_URL)

    @patch("crm.google_maps.requests.get")
    def test_raises_when_no_coordinates(self, get):
        get.return_value = _fake_get("no maps data here")
        with self.assertRaises(ValueError):
            yandex_url_to_google_url(YANDEX_URL)


class ResolveGoogleAddressApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="worker", password="password")

    def test_unauthenticated_access_denied(self):
        response = self.client.post(
            "/api/crm/resolve-google-address/",
            {"address": "Rustaveli 12, Batumi"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    @patch("crm.google_maps.requests.get")
    @patch("crm.yandex_maps.OpenAI")
    def test_google_cache_hit_does_not_call_requests_or_openai(self, openai_cls, get):
        ResolvedYandexAddress.objects.create(
            address="Rustaveli 12, Batumi",
            yandex_url=YANDEX_URL,
        )
        ResolvedGoogleAddress.objects.create(
            address="Rustaveli 12, Batumi",
            google_url=GOOGLE_URL,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/crm/resolve-google-address/",
            {"address": "Rustaveli 12, Batumi"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"url": GOOGLE_URL})
        get.assert_not_called()
        openai_cls.assert_not_called()

    @patch("crm.google_maps.requests.get")
    @patch("crm.yandex_maps.OpenAI")
    def test_google_miss_with_yandex_cache_fetches_and_stores(self, openai_cls, get):
        ResolvedYandexAddress.objects.create(
            address="Rustaveli 12, Batumi",
            yandex_url=YANDEX_URL,
        )
        get.return_value = _fake_get(COORDINATES_HTML)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/crm/resolve-google-address/",
            {"address": "Rustaveli 12, Batumi"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"url": GOOGLE_URL})
        openai_cls.assert_not_called()
        get.assert_called_once()
        cached = ResolvedGoogleAddress.objects.get(address="Rustaveli 12, Batumi")
        self.assertEqual(cached.google_url, GOOGLE_URL)

    @patch("crm.google_maps.requests.get")
    @patch("crm.yandex_maps.OpenAI")
    def test_google_miss_without_yandex_resolves_yandex_then_google(self, openai_cls, get):
        fake_response = MagicMock()
        fake_response.output_text = YANDEX_URL
        openai_cls.return_value.responses.create.return_value = fake_response
        get.return_value = _fake_get(COORDINATES_HTML)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/crm/resolve-google-address/",
            {"address": "Gorgiladze 15, Batumi"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"url": GOOGLE_URL})
        openai_cls.return_value.responses.create.assert_called_once_with(
            prompt={
                "id": YANDEX_MAPS_PROMPT_ID,
                "version": YANDEX_MAPS_PROMPT_VERSION,
            },
            input="Gorgiladze 15, Batumi",
        )
        get.assert_called_once()
        self.assertEqual(
            ResolvedYandexAddress.objects.get(address="Gorgiladze 15, Batumi").yandex_url,
            YANDEX_URL,
        )
        self.assertEqual(
            ResolvedGoogleAddress.objects.get(address="Gorgiladze 15, Batumi").google_url,
            GOOGLE_URL,
        )
