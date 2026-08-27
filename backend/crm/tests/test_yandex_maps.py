from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import ResolvedYandexAddress
from crm.yandex_maps import YANDEX_MAPS_PROMPT_ID, YANDEX_MAPS_PROMPT_VERSION


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
