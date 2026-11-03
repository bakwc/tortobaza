from datetime import datetime, timedelta, timezone as dt_timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings

from crm.models import TelegramChannel, TelegramChannelMessage, TelegramKeyword
from crm.telegram_channels import refresh_keyword_matches, sync_telegram_channels


@override_settings(
    TELEGRAM_API_ID="12345",
    TELEGRAM_API_HASH="hash",
    TELEGRAM_USER_SESSION="session",
)
class SyncTelegramChannelsTests(TestCase):
    def _client(self, entities, messages):
        clients = []

        class FakeTelegramClient:
            def __init__(self, session, api_id, api_hash):
                self.session = session
                self.api_id = api_id
                self.api_hash = api_hash
                self.calls = []
                self.entities = []
                clients.append(self)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def get_entity(self, username):
                self.entities.append(username)
                return entities[username]

            def iter_messages(self, entity, **kwargs):
                self.calls.append({"entity": entity, "kwargs": kwargs})
                return iter(messages[entity.id])

        return FakeTelegramClient, clients

    def test_no_channels_does_not_open_client(self):
        with patch("crm.telegram_channels.TelegramClient") as client:
            sync_telegram_channels()
        client.assert_not_called()

    def test_first_sync_reads_last_month(self):
        now = datetime(2026, 11, 2, 12, 0, tzinfo=dt_timezone.utc)
        entity = SimpleNamespace(id=100, title="Cakes")
        message = SimpleNamespace(
            id=7,
            action=None,
            message="hi",
            date=now - timedelta(days=1),
            sender_id=3,
            sender=SimpleNamespace(username="ann"),
        )
        TelegramChannel.objects.create(username="https://t.me/cakes")
        fake_client, clients = self._client({"cakes": entity}, {100: [message]})
        with (
            patch("crm.telegram_channels.TelegramClient", fake_client),
            patch("crm.telegram_channels.StringSession", side_effect=lambda value: value),
            patch("crm.telegram_channels.timezone.now", return_value=now),
        ):
            sync_telegram_channels()
        kwargs = clients[0].calls[0]["kwargs"]
        self.assertEqual(kwargs["offset_date"], now - timedelta(days=30))
        self.assertIs(kwargs["reverse"], True)
        self.assertNotIn("min_id", kwargs)
        self.assertEqual(clients[0].session, "session")
        self.assertEqual(clients[0].api_id, 12345)
        self.assertEqual(clients[0].api_hash, "hash")
        self.assertEqual(clients[0].entities, ["cakes"])
        row = TelegramChannelMessage.objects.get()
        self.assertEqual(row.text, "hi")
        self.assertEqual(row.message_id, 7)
        self.assertEqual(row.sender_id, 3)
        self.assertEqual(row.sender_username, "ann")
        self.assertEqual(row.sent_at, now - timedelta(days=1))
        channel = TelegramChannel.objects.get()
        self.assertEqual(channel.username, "cakes")
        self.assertEqual(channel.title, "Cakes")
        self.assertEqual(channel.telegram_id, 100)
        self.assertEqual(channel.last_message_id, 7)

    def test_next_sync_uses_cursor_without_duplicates(self):
        now = datetime(2026, 11, 2, 12, 0, tzinfo=dt_timezone.utc)
        entity = SimpleNamespace(id=100, title="Cakes")
        channel = TelegramChannel.objects.create(
            username="cakes",
            title="Cakes",
            telegram_id=100,
            last_message_id=7,
        )
        TelegramChannelMessage.objects.create(
            channel=channel,
            message_id=7,
            sent_at=now - timedelta(days=2),
            text="hi",
            sender_id=3,
            sender_username="ann",
        )
        older = SimpleNamespace(
            id=7,
            action=None,
            message="hi",
            date=now - timedelta(days=2),
            sender_id=3,
            sender=SimpleNamespace(username="ann"),
        )
        newer = SimpleNamespace(
            id=8,
            action=None,
            message="again",
            date=now - timedelta(hours=1),
            sender_id=3,
            sender=SimpleNamespace(username=None),
        )
        fake_client, clients = self._client({"cakes": entity}, {100: [older, newer]})
        with (
            patch("crm.telegram_channels.TelegramClient", fake_client),
            patch("crm.telegram_channels.StringSession", side_effect=lambda value: value),
            patch("crm.telegram_channels.timezone.now", return_value=now),
        ):
            sync_telegram_channels()
        kwargs = clients[0].calls[0]["kwargs"]
        self.assertEqual(kwargs["min_id"], 7)
        self.assertIs(kwargs["reverse"], True)
        self.assertNotIn("offset_date", kwargs)
        self.assertEqual(TelegramChannelMessage.objects.count(), 2)
        self.assertEqual(TelegramChannelMessage.objects.get(message_id=8).text, "again")
        self.assertEqual(TelegramChannelMessage.objects.get(message_id=8).sender_username, "")
        channel.refresh_from_db()
        self.assertEqual(channel.last_message_id, 8)

    def test_disabled_channel_is_not_read(self):
        entity = SimpleNamespace(id=100, title="Cakes")
        TelegramChannel.objects.create(username="off", enabled=False)
        TelegramChannel.objects.create(username="cakes", enabled=True)
        fake_client, clients = self._client({"cakes": entity}, {100: []})
        with (
            patch("crm.telegram_channels.TelegramClient", fake_client),
            patch("crm.telegram_channels.StringSession", side_effect=lambda value: value),
        ):
            sync_telegram_channels()
        self.assertEqual(clients[0].entities, ["cakes"])
        self.assertEqual(len(clients[0].calls), 1)
        self.assertEqual(TelegramChannelMessage.objects.count(), 0)

    def test_keyword_match_is_case_insensitive(self):
        now = datetime(2026, 11, 2, 12, 0, tzinfo=dt_timezone.utc)
        entity = SimpleNamespace(id=100, title="Cakes")
        match_message = SimpleNamespace(
            id=9,
            action=None,
            message="Нужен ТОРТ",
            date=now - timedelta(hours=2),
            sender_id=3,
            sender=SimpleNamespace(username="ann"),
        )
        no_match_message = SimpleNamespace(
            id=10,
            action=None,
            message="привет всем",
            date=now - timedelta(hours=1),
            sender_id=3,
            sender=SimpleNamespace(username="ann"),
        )
        TelegramKeyword.objects.create(word="торт")
        TelegramChannel.objects.create(username="cakes")
        fake_client, _clients = self._client({"cakes": entity}, {100: [match_message, no_match_message]})
        with (
            patch("crm.telegram_channels.TelegramClient", fake_client),
            patch("crm.telegram_channels.StringSession", side_effect=lambda value: value),
            patch("crm.telegram_channels.timezone.now", return_value=now),
        ):
            sync_telegram_channels()
        self.assertIs(TelegramChannelMessage.objects.get(message_id=9).keyword_match, True)
        self.assertIs(TelegramChannelMessage.objects.get(message_id=10).keyword_match, False)

    def test_long_message_is_not_keyword_match(self):
        now = datetime(2026, 11, 2, 12, 0, tzinfo=dt_timezone.utc)
        entity = SimpleNamespace(id=100, title="Cakes")
        long_text = "торт " + "а" * 446
        short_text = "торт " + "а" * 445
        long_message = SimpleNamespace(
            id=11,
            action=None,
            message=long_text,
            date=now - timedelta(hours=2),
            sender_id=3,
            sender=SimpleNamespace(username="ann"),
        )
        short_message = SimpleNamespace(
            id=12,
            action=None,
            message=short_text,
            date=now - timedelta(hours=1),
            sender_id=3,
            sender=SimpleNamespace(username="ann"),
        )
        TelegramKeyword.objects.create(word="торт")
        TelegramChannel.objects.create(username="cakes")
        fake_client, _clients = self._client({"cakes": entity}, {100: [long_message, short_message]})
        with (
            patch("crm.telegram_channels.TelegramClient", fake_client),
            patch("crm.telegram_channels.StringSession", side_effect=lambda value: value),
            patch("crm.telegram_channels.timezone.now", return_value=now),
        ):
            sync_telegram_channels()
        self.assertEqual(TelegramChannelMessage.objects.get(message_id=11).text, long_text)
        self.assertIs(TelegramChannelMessage.objects.get(message_id=11).keyword_match, False)
        self.assertIs(TelegramChannelMessage.objects.get(message_id=12).keyword_match, True)

    def test_sync_rematches_messages_already_stored(self):
        now = datetime(2026, 11, 2, 12, 0, tzinfo=dt_timezone.utc)
        entity = SimpleNamespace(id=100, title="Cakes")
        channel = TelegramChannel.objects.create(
            username="cakes",
            title="Cakes",
            telegram_id=100,
            last_message_id=7,
        )
        stored = TelegramChannelMessage.objects.create(
            channel=channel,
            message_id=7,
            sent_at=now - timedelta(days=1),
            text="нужен медовик на завтра",
            keyword_match=False,
        )
        untouched = TelegramChannelMessage.objects.create(
            channel=channel,
            message_id=6,
            sent_at=now - timedelta(days=2),
            text="привет",
            keyword_match=False,
        )
        TelegramKeyword.objects.create(word="Медовик")
        fake_client, clients = self._client({"cakes": entity}, {100: []})
        with (
            patch("crm.telegram_channels.TelegramClient", fake_client),
            patch("crm.telegram_channels.StringSession", side_effect=lambda value: value),
            patch("crm.telegram_channels.timezone.now", return_value=now),
        ):
            sync_telegram_channels()
        self.assertEqual(clients[0].calls[0]["kwargs"]["min_id"], 7)
        stored.refresh_from_db()
        untouched.refresh_from_db()
        self.assertIs(stored.keyword_match, True)
        self.assertIs(untouched.keyword_match, False)

    def test_refresh_clears_match_when_keyword_is_gone(self):
        channel = TelegramChannel.objects.create(username="cakes")
        message = TelegramChannelMessage.objects.create(
            channel=channel,
            message_id=1,
            sent_at=datetime(2026, 11, 2, 12, 0, tzinfo=dt_timezone.utc),
            text="нужен торт",
            keyword_match=True,
        )
        refresh_keyword_matches()
        message.refresh_from_db()
        self.assertIs(message.keyword_match, False)
