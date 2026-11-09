from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.permissions import grant
from crm.models import LeadVertical, SocialKeyword, SocialLead, SocialMessage, SocialNetwork, SocialSource


class TelegramLeadsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(username="leads-view", password="password")
        self.editor = User.objects.create_user(username="leads-edit", password="password")
        grant(self.viewer, "view_leads")
        grant(self.editor, "edit_leads")
        self.channel = SocialSource.objects.create(
            network=SocialNetwork.objects.get(slug="telegram"),
            username="cakes",
        )
        self.sent_at = timezone.now()

    def _message(
        self,
        message_id: int,
        text: str,
        keyword_match: bool,
        potential_lead: bool | None,
        lead: bool | None = None,
    ) -> SocialMessage:
        external_id = str(message_id)
        message = SocialMessage.objects.create(
            channel=self.channel,
            external_id=external_id,
            url=f"https://t.me/{self.channel.username}/{external_id}",
            sent_at=self.sent_at,
            text=text,
        )
        SocialLead.objects.create(
            message=message,
            vertical=LeadVertical.objects.get(slug="sweet_chill"),
            keyword_match=keyword_match,
            potential_lead=potential_lead,
            lead=lead,
        )
        return message

    def test_messages_default_kind_lead(self):
        lead = self._message(1, "хочу торт", True, True, True)
        self._message(2, "просто чат", True, False, False)
        self._message(3, "торт", True, None)
        self._message(4, "жду проверку", True, True)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/crm/social/messages/")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.json()["results"]]
        self.assertEqual(ids, [lead.id])

    def test_messages_kind_potential(self):
        waiting = self._message(1, "жду", True, True)
        accepted = self._message(2, "лид", True, True, True)
        rejected = self._message(3, "отклонен", True, True, False)
        self._message(4, "нет", True, False, False)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/crm/social/messages/", {"kind": "potential"})
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.json()["results"]]
        self.assertEqual(ids, [rejected.id, accepted.id, waiting.id])

    def test_messages_kind_keyword(self):
        first = self._message(1, "a", True, True)
        second = self._message(2, "b", True, False)
        self._message(3, "c", False, None)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/crm/social/messages/", {"kind": "keyword"})
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.json()["results"]]
        self.assertEqual(set(ids), {first.id, second.id})
        self.assertEqual(len(ids), 2)

    def test_messages_kind_all(self):
        first = self._message(1, "one", False, None)
        second = self._message(2, "two", True, False)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/crm/social/messages/", {"kind": "all"})
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.json()["results"]]
        self.assertEqual(ids, [second.id, first.id])

    def test_messages_q_casefold_cyrillic(self):
        self._message(1, "Хочу ТОРТ", True, True)
        self._message(2, "другое", True, True)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/crm/social/messages/", {"kind": "all", "q": "торт"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["results"]), 1)
        self.assertIn("торт", body["results"][0]["text"].casefold())

    def test_messages_q_excludes_minus_words(self):
        kept = self._message(1, "нужен кондитер", True, True)
        self._message(2, "кондитер в Москва сегодня", True, True)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get(
            "/api/crm/social/messages/",
            {"kind": "all", "q": "кондитер -москва"},
        )
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.json()["results"]]
        self.assertEqual(ids, [kept.id])

    def test_message_url(self):
        msg = self._message(15, "lead", True, True)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/crm/social/messages/", {"kind": "all"})
        row = next(item for item in response.json()["results"] if item["id"] == msg.id)
        self.assertEqual(row["url"], "https://t.me/cakes/15")

    def test_messages_pagination(self):
        for message_id in range(1, 17):
            self._message(message_id, f"m{message_id}", False, None)
        self.client.force_authenticate(user=self.viewer)
        first = self.client.get("/api/crm/social/messages/", {"kind": "all", "page": 1})
        self.assertEqual(first.status_code, 200)
        first_body = first.json()
        self.assertEqual(first_body["page"], 1)
        self.assertEqual(first_body["pages"], 2)
        self.assertEqual(len(first_body["results"]), 15)
        second = self.client.get("/api/crm/social/messages/", {"kind": "all", "page": 2})
        self.assertEqual(second.status_code, 200)
        second_body = second.json()
        self.assertEqual(second_body["page"], 2)
        self.assertEqual(len(second_body["results"]), 1)
        self.assertEqual(second_body["results"][0]["text"], "m1")

    def test_messages_channel_filter(self):
        other = SocialSource.objects.create(
            network=SocialNetwork.objects.get(slug="telegram"),
            username="other",
        )
        on_cakes = self._message(1, "cakes msg", False, None)
        SocialMessage.objects.create(
            channel=other,
            external_id="2",
            url="https://t.me/other/2",
            sent_at=self.sent_at,
            text="other msg",
        )
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get(
            "/api/crm/social/messages/",
            {"kind": "all", "channel": self.channel.id},
        )
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.json()["results"]]
        self.assertEqual(ids, [on_cakes.id])

    def test_messages_vertical_filter(self):
        cake = self._message(1, "торт", True, True, True)
        makeup = self._message(2, "макияж", True, True, False)
        SocialLead.objects.create(
            message=makeup,
            vertical=LeadVertical.objects.get(slug="beauty"),
            keyword_match=True,
            potential_lead=True,
            lead=True,
        )
        self.client.force_authenticate(user=self.viewer)
        beauty = self.client.get("/api/crm/social/messages/", {"vertical": "beauty"})
        self.assertEqual(beauty.status_code, 200)
        self.assertEqual([row["id"] for row in beauty.json()["results"]], [makeup.id])
        sweet = self.client.get("/api/crm/social/messages/", {"vertical": "sweet_chill"})
        self.assertEqual([row["id"] for row in sweet.json()["results"]], [cake.id])

    def test_messages_network_filter(self):
        threads = SocialSource.objects.create(
            network=SocialNetwork.objects.create(slug="threads", name="Threads"),
            username="батуми торт",
        )
        self._message(1, "telegram msg", False, None)
        SocialMessage.objects.create(
            channel=threads,
            external_id="2",
            url="https://www.threads.com/@x/post/2",
            sent_at=self.sent_at,
            text="threads msg",
        )
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get(
            "/api/crm/social/messages/",
            {"kind": "all", "network": "threads"},
        )
        self.assertEqual(response.status_code, 200)
        texts = [row["text"] for row in response.json()["results"]]
        self.assertEqual(texts, ["threads msg"])

    def test_viewer_cannot_create_channel(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post(
            "/api/crm/social/channels/",
            {"username": "https://t.me/new_channel/", "enabled": True},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_editor_normalizes_channel_username(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.post(
            "/api/crm/social/channels/",
            {"username": "https://t.me/new_channel/", "enabled": True},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["username"], "new_channel")

    def test_keyword_crud(self):
        self.client.force_authenticate(user=self.editor)
        sweet = LeadVertical.objects.get(slug="sweet_chill")
        beauty = LeadVertical.objects.get(slug="beauty")
        created = self.client.post(
            "/api/crm/social/keywords/",
            {"word": "медовик", "vertical": sweet.id},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        keyword_id = created.json()["id"]
        same_word = self.client.post(
            "/api/crm/social/keywords/",
            {"word": "медовик", "vertical": beauty.id},
            format="json",
        )
        self.assertEqual(same_word.status_code, 201)
        updated = self.client.put(
            f"/api/crm/social/keywords/{keyword_id}/",
            {"word": "торт", "vertical": sweet.id},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(SocialKeyword.objects.get(pk=keyword_id).word, "торт")
        deleted = self.client.delete(f"/api/crm/social/keywords/{keyword_id}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(SocialKeyword.objects.filter(pk=keyword_id).exists())
        self.assertTrue(SocialKeyword.objects.filter(pk=same_word.json()["id"]).exists())

    def test_keyword_change_rematches_stored_messages(self):
        self.client.force_authenticate(user=self.editor)
        medovik = self._message(1, "закажу медовик", False, None)
        cake = self._message(2, "хочу торт", False, None)
        sweet = LeadVertical.objects.get(slug="sweet_chill")
        created = self.client.post(
            "/api/crm/social/keywords/",
            {"word": "медовик", "vertical": sweet.id},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertIs(medovik.leads.get(vertical=sweet).keyword_match, True)
        self.assertIs(cake.leads.get(vertical=sweet).keyword_match, False)
        self.assertIs(medovik.leads.get(vertical__slug="beauty").keyword_match, False)
        updated = self.client.put(
            f"/api/crm/social/keywords/{created.json()['id']}/",
            {"word": "торт", "vertical": sweet.id},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertIs(medovik.leads.get(vertical=sweet).keyword_match, False)
        self.assertIs(cake.leads.get(vertical=sweet).keyword_match, True)
        deleted = self.client.delete(f"/api/crm/social/keywords/{created.json()['id']}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertIs(cake.leads.get(vertical=sweet).keyword_match, False)
