from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import SocialKeyword, SocialMessage, SocialNetwork, SocialSource

TOKEN = "ingest-token"


def _message_body(**overrides) -> dict:
    body = {
        "network": "facebook",
        "source_key": "group-123",
        "source_title": "Батуми чат",
        "external_id": "post-1",
        "url": "https://facebook.com/groups/group-123/posts/post-1",
        "text": "хочу торт",
        "sent_at": "2026-11-03T12:00:00Z",
        "sender_id": "999",
        "sender_username": "ivan",
    }
    body.update(overrides)
    return body


@override_settings(SOCIAL_INGEST_TOKEN=TOKEN)
class SocialIngestTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_missing_token_is_forbidden(self):
        response = self.client.get("/api/social/networks/")
        self.assertEqual(response.status_code, 403)

    def test_wrong_token_is_forbidden(self):
        response = self.client.post(
            "/api/social/networks/",
            {"slug": "facebook", "name": "Facebook"},
            format="json",
            HTTP_AUTHORIZATION="Bearer nope",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(SOCIAL_INGEST_TOKEN="")
    def test_empty_configured_token_is_forbidden(self):
        response = self.client.get(
            "/api/social/networks/",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(response.status_code, 403)

    def test_create_network_and_reject_duplicate(self):
        created = self.client.post(
            "/api/social/networks/",
            {"slug": "facebook", "name": "Facebook"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["slug"], "facebook")
        listed = self.client.get(
            "/api/social/networks/",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(listed.status_code, 200)
        slugs = [row["slug"] for row in listed.json()]
        self.assertIn("facebook", slugs)
        self.assertIn("telegram", slugs)
        again = self.client.post(
            "/api/social/networks/",
            {"slug": "facebook", "name": "Facebook"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(again.status_code, 400)

    def test_message_requires_known_network(self):
        response = self.client.post(
            "/api/social/messages/",
            _message_body(),
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SocialMessage.objects.count(), 0)

    def test_message_sets_keyword_match_and_repeat_keeps_lead_flag(self):
        SocialKeyword.objects.create(word="торт")
        self.client.post(
            "/api/social/networks/",
            {"slug": "facebook", "name": "Facebook"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        created = self.client.post(
            "/api/social/messages/",
            _message_body(),
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(created.status_code, 201)
        self.assertIs(created.json()["keyword_match"], True)
        stored = SocialMessage.objects.get(external_id="post-1")
        stored.keyword_match = False
        stored.save(update_fields=["keyword_match"])
        same = self.client.post(
            "/api/social/messages/",
            _message_body(),
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(same.status_code, 200)
        stored.refresh_from_db()
        self.assertIs(stored.keyword_match, False)
        self.assertEqual(stored.text, "хочу торт")
        missed = self.client.post(
            "/api/social/messages/",
            _message_body(external_id="post-2", text="просто чат"),
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(missed.status_code, 201)
        self.assertIs(missed.json()["keyword_match"], False)
        message = SocialMessage.objects.get(external_id="post-1")
        message.potential_lead = False
        message.lead_notified = True
        message.save(update_fields=["potential_lead", "lead_notified"])
        updated = self.client.post(
            "/api/social/messages/",
            _message_body(text="хочу торт ещё", source_title="Новый чат"),
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(updated.status_code, 200)
        message.refresh_from_db()
        self.assertEqual(message.text, "хочу торт ещё")
        self.assertIs(message.keyword_match, True)
        self.assertIs(message.potential_lead, False)
        self.assertIs(message.lead_notified, True)
        self.assertEqual(message.sender_id, "999")
        self.assertEqual(message.channel.network.slug, "facebook")
        self.assertEqual(message.channel.username, "group-123")
        self.assertEqual(message.channel.title, "Новый чат")
        self.assertEqual(SocialSource.objects.filter(network__slug="facebook").count(), 1)
        self.assertEqual(SocialMessage.objects.count(), 2)

    def test_telegram_source_key_is_normalized(self):
        created = self.client.post(
            "/api/social/messages/",
            _message_body(
                network="telegram",
                source_key="https://t.me/cakes/",
                source_title="Cakes",
                external_id="15",
                url="https://t.me/cakes/15",
            ),
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(created.status_code, 201)
        source = SocialSource.objects.get(username="cakes")
        self.assertEqual(source.network.slug, "telegram")
        again = self.client.post(
            "/api/social/messages/",
            _message_body(
                network="telegram",
                source_key="cakes",
                source_title="Cakes",
                external_id="15",
                url="https://t.me/cakes/15",
                text="ещё",
            ),
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(again.status_code, 200)
        self.assertEqual(SocialNetwork.objects.get(slug="telegram").sources.count(), 1)
        self.assertEqual(SocialMessage.objects.get().text, "ещё")
