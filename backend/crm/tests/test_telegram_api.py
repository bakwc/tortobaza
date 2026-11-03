from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.permissions import grant
from crm.models import TelegramChannel, TelegramChannelMessage, TelegramKeyword


class TelegramLeadsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(username="leads-view", password="password")
        self.editor = User.objects.create_user(username="leads-edit", password="password")
        grant(self.viewer, "view_leads")
        grant(self.editor, "edit_leads")
        self.channel = TelegramChannel.objects.create(username="cakes")
        self.sent_at = timezone.now()

    def _message(
        self,
        message_id: int,
        text: str,
        keyword_match: bool,
        potential_lead: bool | None,
    ) -> TelegramChannelMessage:
        return TelegramChannelMessage.objects.create(
            channel=self.channel,
            message_id=message_id,
            sent_at=self.sent_at,
            text=text,
            keyword_match=keyword_match,
            potential_lead=potential_lead,
        )

    def test_messages_default_kind_lead(self):
        lead = self._message(1, "хочу торт", True, True)
        self._message(2, "просто чат", True, False)
        self._message(3, "торт", True, None)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/crm/telegram/messages/")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.json()]
        self.assertEqual(ids, [lead.id])

    def test_messages_kind_keyword(self):
        first = self._message(1, "a", True, True)
        second = self._message(2, "b", True, False)
        self._message(3, "c", False, None)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/crm/telegram/messages/", {"kind": "keyword"})
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.json()]
        self.assertEqual(set(ids), {first.id, second.id})
        self.assertEqual(len(ids), 2)

    def test_messages_kind_all(self):
        first = self._message(1, "one", False, None)
        second = self._message(2, "two", True, False)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/crm/telegram/messages/", {"kind": "all"})
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.json()]
        self.assertEqual(ids, [second.id, first.id])

    def test_messages_q_casefold_cyrillic(self):
        self._message(1, "Хочу ТОРТ", True, True)
        self._message(2, "другое", True, True)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/crm/telegram/messages/", {"kind": "all", "q": "торт"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertIn("торт", response.json()[0]["text"].casefold())

    def test_message_url(self):
        msg = self._message(15, "lead", True, True)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/crm/telegram/messages/", {"kind": "all"})
        row = next(item for item in response.json() if item["id"] == msg.id)
        self.assertEqual(row["url"], "https://t.me/cakes/15")

    def test_viewer_cannot_create_channel(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post(
            "/api/crm/telegram/channels/",
            {"username": "https://t.me/new_channel/", "enabled": True},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_editor_normalizes_channel_username(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.post(
            "/api/crm/telegram/channels/",
            {"username": "https://t.me/new_channel/", "enabled": True},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["username"], "new_channel")

    def test_keyword_crud(self):
        self.client.force_authenticate(user=self.editor)
        created = self.client.post("/api/crm/telegram/keywords/", {"word": "медовик"}, format="json")
        self.assertEqual(created.status_code, 201)
        keyword_id = created.json()["id"]
        updated = self.client.put(
            f"/api/crm/telegram/keywords/{keyword_id}/",
            {"word": "торт"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(TelegramKeyword.objects.get(pk=keyword_id).word, "торт")
        deleted = self.client.delete(f"/api/crm/telegram/keywords/{keyword_id}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(TelegramKeyword.objects.filter(pk=keyword_id).exists())
