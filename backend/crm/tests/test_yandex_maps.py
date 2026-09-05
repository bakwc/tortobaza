from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import ResolvedYandexAddress
from crm.yandex_maps import YANDEX_MAPS_PROMPT_ID, YANDEX_MAPS_PROMPT_VERSION

INSTAGRAM_URL = (
    "https://l.instagram.com/?u=https%3A%2F%2Fmaps.app.goo.gl%2F"
    "NUxbTdCBazTb1jvV8%3Fg_st%3Dii&e=signature"
)
GOOGLE_SHORT_URL = "https://maps.app.goo.gl/NUxbTdCBazTb1jvV8?g_st=ii"
GOOGLE_CONTINUE_URL = (
    "https://maps.google.com/maps?q=MM8M%2B5HP%2BTamar%2BMepe%2B1"
    "&ftid=place-id"
)
GOOGLE_CONSENT_URL = (
    "https://consent.google.com/ml?continue=https%3A%2F%2Fmaps.google.com%2Fmaps"
    "%3Fq%3DMM8M%252B5HP%252BTamar%252BMepe%252B1%26ftid%3Dplace-id"
    "&gl=DE&hl=de"
)


class ResolveYandexAddressApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="worker", password="password")

    def test_unauthenticated_access_denied(self):
        response = self.client.post(
            "/api/crm/resolve-yandex-address/",
            {"address": "Rustaveli 12, Batumi"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    @patch("crm.yandex_maps.OpenAI")
    def test_cache_hit_does_not_call_openai(self, openai_cls):
        ResolvedYandexAddress.objects.create(
            address="Rustaveli 12, Batumi",
            yandex_url="https://yandex.com/maps/?text=Rustaveli",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/crm/resolve-yandex-address/",
            {"address": "Rustaveli 12, Batumi"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"url": "https://yandex.com/maps/?text=Rustaveli"})
        openai_cls.assert_not_called()

    @patch("crm.yandex_maps.OpenAI")
    def test_cache_miss_calls_openai_and_stores(self, openai_cls):
        fake_response = MagicMock()
        fake_response.output_text = "https://yandex.com/maps/?text=Gorgiladze"
        openai_cls.return_value.responses.create.return_value = fake_response
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/crm/resolve-yandex-address/",
            {"address": "Gorgiladze 15, Batumi"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"url": "https://yandex.com/maps/?text=Gorgiladze"})
        openai_cls.return_value.responses.create.assert_called_once_with(
            prompt={
                "id": YANDEX_MAPS_PROMPT_ID,
                "version": YANDEX_MAPS_PROMPT_VERSION,
            },
            input="Gorgiladze 15, Batumi",
        )
        cached = ResolvedYandexAddress.objects.get(address="Gorgiladze 15, Batumi")
        self.assertEqual(cached.yandex_url, "https://yandex.com/maps/?text=Gorgiladze")

    @patch("crm.google_maps.requests.get")
    @patch("crm.yandex_maps.OpenAI")
    def test_instagram_address_is_unwrapped_before_openai(self, openai_cls, get):
        response = MagicMock()
        response.url = GOOGLE_CONSENT_URL
        response.raise_for_status = MagicMock()
        get.return_value = response
        fake_response = MagicMock()
        fake_response.output_text = "https://yandex.com/maps/?text=Tamar"
        openai_cls.return_value.responses.create.return_value = fake_response
        self.client.force_authenticate(user=self.user)
        api_response = self.client.post(
            "/api/crm/resolve-yandex-address/",
            {"address": INSTAGRAM_URL},
            format="json",
        )
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            api_response.json(),
            {"url": "https://yandex.com/maps/?text=Tamar"},
        )
        openai_cls.return_value.responses.create.assert_called_once_with(
            prompt={
                "id": YANDEX_MAPS_PROMPT_ID,
                "version": YANDEX_MAPS_PROMPT_VERSION,
            },
            input=GOOGLE_CONTINUE_URL,
        )
        get.assert_called_once()
        self.assertEqual(get.call_args.args[0], GOOGLE_SHORT_URL)
        cached = ResolvedYandexAddress.objects.get(address=INSTAGRAM_URL)
        self.assertEqual(cached.yandex_url, "https://yandex.com/maps/?text=Tamar")
