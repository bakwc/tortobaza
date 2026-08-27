import json
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from crm.whatsapp import check_number, get_new_qr


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

    def test_admin_page_renders_form(self):
        User.objects.create_superuser(username="admin", password="password")
        client = Client()
        client.login(username="admin", password="password")
        response = client.get("/admin/crm/whatsappnumbercheck/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="number"')
        self.assertNotContains(response, "<th>Exists</th>")

    def test_admin_check_shows_result(self):
        User.objects.create_superuser(username="admin", password="password")
        client = Client()
        client.login(username="admin", password="password")
        payload = {
            "number": "995595589443",
            "exists": True,
            "whatsappId": "225219746779246@lid",
        }
        with patch("crm.admin.check_number", return_value=payload) as check:
            response = client.get(
                "/admin/crm/whatsappnumbercheck/",
                {"number": "995595589443"},
            )
        check.assert_called_once_with("995595589443")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "995595589443")
        self.assertContains(response, "225219746779246@lid")
        self.assertContains(response, "True")

    def test_get_new_qr_stops_starts_then_fetches_qr(self):
        calls = []
        qr_payload = {
            "qrCode": "data:image/png;base64,abc",
            "status": "qr_ready",
        }

        def urlopen(req, timeout=None):
            calls.append((req.get_method(), req.full_url))
            if req.full_url.endswith("/stop"):
                return FakeHttpResponse({"status": "disconnected"})
            if req.full_url.endswith("/start"):
                return FakeHttpResponse({"status": "initializing"})
            if req.full_url.endswith("/qr"):
                return FakeHttpResponse(qr_payload)
            raise AssertionError(req.full_url)

        with (
            patch("crm.whatsapp.urllib.request.urlopen", side_effect=urlopen),
            patch("crm.whatsapp.time.sleep") as sleep,
        ):
            result = get_new_qr()
        sleep.assert_called_once_with(5)
        self.assertEqual(result, qr_payload)
        self.assertEqual(
            calls,
            [
                ("POST", "http://localhost:2785/api/sessions/sess-1/stop"),
                ("POST", "http://localhost:2785/api/sessions/sess-1/start"),
                ("GET", "http://localhost:2785/api/sessions/sess-1/qr"),
            ],
        )

    def test_admin_qr_page_renders_button(self):
        User.objects.create_superuser(username="admin", password="password")
        client = Client()
        client.login(username="admin", password="password")
        response = client.get("/admin/crm/whatsappgetnewqr/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Get new QR")
        self.assertNotContains(response, 'alt="WhatsApp QR"')

    def test_admin_qr_post_shows_image(self):
        User.objects.create_superuser(username="admin", password="password")
        client = Client()
        client.login(username="admin", password="password")
        payload = {
            "qrCode": "data:image/png;base64,abc",
            "status": "qr_ready",
        }
        with patch("crm.admin.get_new_qr", return_value=payload) as fetch:
            response = client.post("/admin/crm/whatsappgetnewqr/")
        fetch.assert_called_once_with()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'src="data:image/png;base64,abc"')
        self.assertContains(response, "qr_ready")
