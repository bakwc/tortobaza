import json
import tempfile
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from telethon.errors.rpcerrorlist import PhoneNotOccupiedError
from telethon.tl.functions.contacts import ResolvePhoneRequest

from crm.telegram_user import resolve_phone


class Clock:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now


class TelegramUserTests(TestCase):
    def setUp(self):
        self.state_dir = tempfile.TemporaryDirectory()
        self.state_path = str(Path(self.state_dir.name) / "state")
        self.settings_override = override_settings(
            TELEGRAM_API_ID="12345",
            TELEGRAM_API_HASH="hash",
            TELEGRAM_USER_SESSION="session",
            TELEGRAM_RESOLVE_STATE_PATH=self.state_path,
        )
        self.settings_override.enable()
        self.clock = Clock()

    def tearDown(self):
        self.settings_override.disable()
        self.state_dir.cleanup()

    def _client(self, result, error):
        clients = []

        class FakeTelegramClient:
            def __init__(self, session, api_id, api_hash):
                self.session = session
                self.api_id = api_id
                self.api_hash = api_hash
                self.requests = []
                clients.append(self)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def __call__(self, request):
                self.requests.append(request)
                if error is not None:
                    raise error
                return result

        return FakeTelegramClient, clients

    def test_resolve_phone_found(self):
        peer = SimpleNamespace(users=[SimpleNamespace(id=424242, username="anna")])
        fake_client, clients = self._client(peer, None)
        with (
            patch("crm.telegram_user.TelegramClient", fake_client),
            patch("crm.telegram_user.StringSession", side_effect=lambda value: value),
            patch("crm.telegram_user.time.time", self.clock.time),
            patch("crm.telegram_user.time.sleep") as sleep,
        ):
            result = resolve_phone("995595589443")
        sleep.assert_not_called()
        self.assertEqual(
            result,
            {
                "number": "995595589443",
                "resolved": True,
                "user_id": 424242,
                "username": "anna",
            },
        )
        self.assertEqual(clients[0].api_id, 12345)
        self.assertEqual(clients[0].api_hash, "hash")
        self.assertEqual(clients[0].session, "session")
        self.assertEqual(clients[0].requests[0].phone, "+995595589443")

    def test_resolve_phone_not_occupied(self):
        error = PhoneNotOccupiedError(ResolvePhoneRequest(phone="+995595589441"))
        fake_client, clients = self._client(None, error)
        with (
            patch("crm.telegram_user.TelegramClient", fake_client),
            patch("crm.telegram_user.StringSession", side_effect=lambda value: value),
            patch("crm.telegram_user.time.time", self.clock.time),
            patch("crm.telegram_user.time.sleep"),
        ):
            result = resolve_phone("995595589441")
        self.assertEqual(
            result,
            {
                "number": "995595589441",
                "resolved": False,
                "user_id": None,
                "username": None,
            },
        )
        self.assertEqual(clients[0].requests[0].phone, "+995595589441")

    def test_second_call_waits_remaining_interval(self):
        peer = SimpleNamespace(users=[SimpleNamespace(id=7, username=None)])
        fake_client, clients = self._client(peer, None)
        with (
            patch("crm.telegram_user.TelegramClient", fake_client),
            patch("crm.telegram_user.StringSession", side_effect=lambda value: value),
            patch("crm.telegram_user.time.time", self.clock.time),
            patch("crm.telegram_user.time.sleep") as sleep,
        ):
            resolve_phone("995595589443")
            self.clock.now = 1001.0
            result = resolve_phone("+995595589443")
        sleep.assert_called_once_with(2.0)
        self.assertEqual(clients[0].requests[0].phone, "+995595589443")
        self.assertEqual(clients[1].requests[0].phone, "+995595589443")
        self.assertTrue(result["resolved"])
        self.assertIsNone(result["username"])

    def test_command_prints_json(self):
        peer = SimpleNamespace(users=[SimpleNamespace(id=424242, username="anna")])
        fake_client, _clients = self._client(peer, None)
        out = StringIO()
        with (
            patch("crm.telegram_user.TelegramClient", fake_client),
            patch("crm.telegram_user.StringSession", side_effect=lambda value: value),
            patch("crm.telegram_user.time.time", self.clock.time),
            patch("crm.telegram_user.time.sleep"),
        ):
            call_command("check_telegram_number", "995595589443", stdout=out)
        self.assertEqual(
            json.loads(out.getvalue()),
            {
                "number": "995595589443",
                "resolved": True,
                "user_id": 424242,
                "username": "anna",
            },
        )

    def test_admin_page_renders_form(self):
        User.objects.create_superuser(username="admin", password="password")
        client = Client()
        client.login(username="admin", password="password")
        response = client.get("/admin/crm/telegramnumbercheck/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="number"')
        self.assertNotContains(response, "<th>Resolved</th>")

    def test_admin_check_shows_result(self):
        User.objects.create_superuser(username="admin", password="password")
        client = Client()
        client.login(username="admin", password="password")
        payload = {
            "number": "995595589443",
            "resolved": True,
            "user_id": 424242,
            "username": "anna",
        }
        with patch("crm.admin.resolve_phone", return_value=payload) as check:
            response = client.get(
                "/admin/crm/telegramnumbercheck/",
                {"number": "995595589443"},
            )
        check.assert_called_once_with("995595589443")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "995595589443")
        self.assertContains(response, "424242")
        self.assertContains(response, "anna")
        self.assertContains(response, "True")
