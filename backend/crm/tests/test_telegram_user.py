import json
import tempfile
from datetime import time, timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from telethon.errors.rpcerrorlist import PhoneNotOccupiedError
from telethon.tl.functions.contacts import ResolvePhoneRequest

from crm.models import CrmOrder, ResolvedTelegramPhone
from crm.telegram_user import resolve_phone

_TB = ZoneInfo("Asia/Tbilisi")


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


def _found(number: str) -> dict:
    return {
        "number": number,
        "resolved": True,
        "user_id": int(number[-6:]),
        "username": f"u{number[-4:]}",
    }


class SyncTelegramPhoneTests(TestCase):
    def _order(self, *, date, contact, nickname="", time_start=time(12, 0)):
        return CrmOrder.objects.create(
            date=date,
            time_start=time_start,
            contact=contact,
            nickname=nickname,
            weight="1kg",
            filling="Vanilla",
            cake_price=Decimal("100.00"),
        )

    def _sync(self, resolve):
        with (
            patch("crm.management.commands.sync_crm_orders_to_telegram.sync_flowwow_orders"),
            patch("crm.management.commands.sync_crm_orders_to_telegram.sync_crm_order_to_telegram"),
            patch("crm.management.commands.sync_crm_orders_to_telegram.resolve_phone", resolve),
        ):
            call_command("sync_crm_orders_to_telegram")

    def test_checks_five_then_the_rest_on_the_next_sync(self):
        today = timezone.now().astimezone(_TB).date()
        numbers = [f"99555500000{index}" for index in range(1, 7)]
        for index, number in enumerate(numbers):
            self._order(date=today + timedelta(days=index), contact=number)
        called = []

        def resolve(number):
            called.append(number)
            return _found(number)

        self._sync(resolve)
        self.assertEqual(called, numbers[:5])
        self.assertEqual(
            list(ResolvedTelegramPhone.objects.order_by("number").values_list("number", flat=True)),
            numbers[:5],
        )
        called.clear()
        self._sync(resolve)
        self.assertEqual(called, numbers[5:])
        self.assertEqual(ResolvedTelegramPhone.objects.count(), 6)

    def test_skips_delivery_date_older_than_one_day(self):
        now = timezone.now().astimezone(_TB)
        cutoff = (now - timedelta(days=1)).date()
        self._order(date=cutoff - timedelta(days=1), contact="995555000001")
        self._order(date=cutoff, contact="995555000002")
        called = []

        def resolve(number):
            called.append(number)
            return _found(number)

        self._sync(resolve)
        self.assertEqual(called, ["995555000002"])

    def test_skips_telegram_username(self):
        today = timezone.now().astimezone(_TB).date()
        self._order(date=today, contact="995555000001", nickname="@anna")
        called = []

        def resolve(number):
            called.append(number)
            return _found(number)

        self._sync(resolve)
        self.assertEqual(called, ["995555000001"])

    def test_same_number_on_two_orders_is_checked_once(self):
        today = timezone.now().astimezone(_TB).date()
        self._order(date=today, contact="995555000001", time_start=time(10, 0))
        self._order(date=today, contact="995555000001", time_start=time(11, 0))
        called = []

        def resolve(number):
            called.append(number)
            return _found(number)

        self._sync(resolve)
        self.assertEqual(called, ["995555000001"])
        self.assertEqual(ResolvedTelegramPhone.objects.count(), 1)

    def test_unresolved_number_is_stored_and_not_checked_again(self):
        today = timezone.now().astimezone(_TB).date()
        self._order(date=today, contact="995555000001")
        called = []

        def resolve(number):
            called.append(number)
            return {
                "number": number,
                "resolved": False,
                "user_id": None,
                "username": None,
            }

        self._sync(resolve)
        row = ResolvedTelegramPhone.objects.get()
        self.assertEqual(row.number, "995555000001")
        self.assertFalse(row.resolved)
        self.assertIsNone(row.user_id)
        self.assertEqual(row.username, "")
        self._sync(resolve)
        self.assertEqual(called, ["995555000001"])


class ResolvedTelegramPhoneAdminTests(TestCase):
    def test_list_shows_row_and_add_is_forbidden(self):
        User.objects.create_superuser(username="admin", password="password")
        ResolvedTelegramPhone.objects.create(
            number="995595589443",
            resolved=True,
            user_id=424242,
            username="anna",
        )
        client = Client()
        client.login(username="admin", password="password")
        response = client.get("/admin/crm/resolvedtelegramphone/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "995595589443")
        self.assertContains(response, "anna")
        add = client.get("/admin/crm/resolvedtelegramphone/add/")
        self.assertEqual(add.status_code, 403)
