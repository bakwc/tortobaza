import json
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from crm.whatsapp import check_number


class FakeHttpResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@override_settings(
    WHATSAPP_OWA_BASE_URL="http://localhost:2785",
    WHATSAPP_OWA_SESSION_ID="sess-1",
    WHATSAPP_OWA_API_KEY="secret-key",
)
class WhatsAppTests(TestCase):
    def test_check_number_exists(self):
        payload = {
            "number": "995595589443",
            "exists": True,
            "whatsappId": "225219746779246@lid",
        }
        with patch(
            "crm.whatsapp.urllib.request.urlopen",
            return_value=FakeHttpResponse(payload),
        ) as urlopen:
            result = check_number("995595589443")
        self.assertEqual(result, payload)
        req = urlopen.call_args[0][0]
        self.assertEqual(
            req.full_url,
            "http://localhost:2785/api/sessions/sess-1/contacts/check/995595589443",
        )
        self.assertEqual(req.get_header("Accept"), "application/json")
        self.assertEqual(req.get_header("X-api-key"), "secret-key")

    def test_check_number_missing(self):
        payload = {"number": "995595589441", "exists": False, "whatsappId": None}
        with patch(
            "crm.whatsapp.urllib.request.urlopen",
            return_value=FakeHttpResponse(payload),
        ):
            result = check_number("995595589441")
        self.assertEqual(result, payload)

    def test_command_prints_json(self):
        payload = {
            "number": "995595589443",
            "exists": True,
            "whatsappId": "225219746779246@lid",
        }
        out = StringIO()
        with patch(
            "crm.whatsapp.urllib.request.urlopen",
            return_value=FakeHttpResponse(payload),
        ):
            call_command("check_whatsapp_number", "995595589443", stdout=out)
        self.assertEqual(json.loads(out.getvalue()), payload)
