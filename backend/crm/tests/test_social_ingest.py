from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import SocialKeyword, SocialMessage, SocialNetwork, SocialSource

TOKEN = "ingest-token"


def _item(**overrides) -> dict:
    item = {
        "source_key": "group-123",
        "source_title": "Батуми чат",
        "external_id": "post-1",
        "url": "https://facebook.com/groups/group-123/posts/post-1",
        "text": "хочу торт",
        "sent_at": "2026-11-03T12:00:00Z",
        "sender_id": "999",
        "sender_username": "ivan",
        "location": "Batumi, Georgia",
        "topic": "Батуми",
    }
    item.update(overrides)
    return item


def _message_body(network: str = "facebook", messages: list[dict] | None = None) -> dict:
    return {
        "network": network,
        "messages": [_item()] if messages is None else messages,
    }


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

    def test_batch_creates_messages_and_skips_duplicates(self):
        SocialKeyword.objects.create(word="торт")
        self.client.post(
            "/api/social/networks/",
            {"slug": "facebook", "name": "Facebook"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        created = self.client.post(
            "/api/social/messages/",
            _message_body(
                messages=[
                    _item(),
                    _item(external_id="post-2", text="просто чат", source_key="other", source_title="Другой"),
                    _item(external_id="post-1", text="повтор в батче", source_key="elsewhere"),
                ]
            ),
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json(), {"created": 2, "skipped": 1})
        stored = SocialMessage.objects.get(external_id="post-1")
        self.assertIs(stored.keyword_match, True)
        self.assertEqual(stored.location, "Batumi, Georgia")
        self.assertEqual(stored.topic, "Батуми")
        self.assertEqual(stored.channel.username, "group-123")
        self.assertEqual(stored.sender_id, "999")
        missed = SocialMessage.objects.get(external_id="post-2")
        self.assertIs(missed.keyword_match, False)
        stored.potential_lead = False
        stored.lead_notified = True
        stored.save(update_fields=["potential_lead", "lead_notified"])
        again = self.client.post(
            "/api/social/messages/",
            _message_body(
                messages=[
                    _item(text="хочу торт ещё", source_title="Новый чат", source_key="new-group"),
                    _item(
                        external_id="post-2",
                        text="другой канал",
                        source_key="third",
                        source_title="Третий",
                    ),
                ]
            ),
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json(), {"created": 0, "skipped": 2})
        stored.refresh_from_db()
        self.assertEqual(stored.text, "хочу торт")
        self.assertIs(stored.keyword_match, True)
        self.assertIs(stored.potential_lead, False)
        self.assertIs(stored.lead_notified, True)
        self.assertEqual(stored.channel.username, "group-123")
        self.assertEqual(stored.channel.title, "Батуми чат")
        missed.refresh_from_db()
        self.assertEqual(missed.text, "просто чат")
        self.assertEqual(missed.channel.username, "other")
        self.assertEqual(SocialMessage.objects.count(), 2)
        self.assertEqual(SocialSource.objects.filter(network__slug="facebook").count(), 2)

    def test_telegram_source_key_is_normalized(self):
        created = self.client.post(
            "/api/social/messages/",
            _message_body(
                network="telegram",
                messages=[
                    _item(
                        source_key="https://t.me/cakes/",
                        source_title="Cakes",
                        external_id="15",
                        url="https://t.me/cakes/15",
                    )
                ],
            ),
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json(), {"created": 1, "skipped": 0})
        source = SocialSource.objects.get(username="cakes")
        self.assertEqual(source.network.slug, "telegram")
        again = self.client.post(
            "/api/social/messages/",
            _message_body(
                network="telegram",
                messages=[
                    _item(
                        source_key="cakes",
                        source_title="Cakes",
                        external_id="15",
                        url="https://t.me/cakes/15",
                        text="ещё",
                    )
                ],
            ),
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json(), {"created": 0, "skipped": 1})
        self.assertEqual(SocialNetwork.objects.get(slug="telegram").sources.count(), 1)
        self.assertEqual(SocialMessage.objects.get().text, "хочу торт")

    def test_process_leads_missing_token_is_forbidden(self):
        response = self.client.post("/api/social/networks/threads/process-leads/")
        self.assertEqual(response.status_code, 403)

    def test_process_leads_unknown_network(self):
        response = self.client.post(
            "/api/social/networks/threads/process-leads/",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(response.status_code, 404)

    def test_process_leads_telegram_is_rejected(self):
        response = self.client.post(
            "/api/social/networks/telegram/process-leads/",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(response.status_code, 400)

    @patch("crm.telegram_views.notify_recent_leads")
    @patch("crm.telegram_views.classify_leads")
    def test_process_leads_runs_for_network(self, classify_leads, notify_recent_leads):
        SocialNetwork.objects.create(slug="threads", name="Threads")
        response = self.client.post(
            "/api/social/networks/threads/process-leads/",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(response.status_code, 204)
        classify_leads.assert_called_once_with("threads", False)
        notify_recent_leads.assert_called_once_with("threads")

    @patch("crm.telegram_views.notify_recent_leads")
    @patch("crm.telegram_views.classify_leads")
    def test_process_leads_potential_mode(self, classify_leads, notify_recent_leads):
        SocialNetwork.objects.create(slug="threads", name="Threads")
        response = self.client.post(
            "/api/social/networks/threads/process-leads/?potential=true",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(response.status_code, 204)
        classify_leads.assert_called_once_with("threads", True)
        notify_recent_leads.assert_called_once_with("threads")

    def test_process_leads_rejects_bad_potential(self):
        SocialNetwork.objects.create(slug="threads", name="Threads")
        response = self.client.post(
            "/api/social/networks/threads/process-leads/?potential=maybe",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(response.status_code, 400)

    def test_potential_leads_lists_rows_without_context(self):
        network = SocialNetwork.objects.create(slug="threads", name="Threads")
        source = SocialSource.objects.create(network=network, username="батуми торт")
        waiting = SocialMessage.objects.create(
            channel=source,
            external_id="1",
            url="https://www.threads.com/@a/post/1",
            sent_at="2026-11-04T08:00:00Z",
            text="бенто",
            sender_username="a",
            potential_lead=True,
        )
        SocialMessage.objects.create(
            channel=source,
            external_id="2",
            url="https://www.threads.com/@a/post/2",
            sent_at="2026-11-04T08:00:00Z",
            text="есть контекст",
            potential_lead=True,
            context=[],
        )
        SocialMessage.objects.create(
            channel=source,
            external_id="3",
            url="https://www.threads.com/@a/post/3",
            sent_at="2026-11-04T08:00:00Z",
            text="уже лид",
            potential_lead=True,
            lead=True,
        )
        missing = self.client.get("/api/social/networks/threads/potential-leads/")
        self.assertEqual(missing.status_code, 403)
        response = self.client.get(
            "/api/social/networks/threads/potential-leads/",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([row["id"] for row in body], [waiting.id])
        self.assertEqual(body[0]["url"], waiting.url)
        self.assertEqual(body[0]["text"], "бенто")
        self.assertEqual(body[0]["sender_username"], "a")

    def test_context_saves_thread(self):
        network = SocialNetwork.objects.create(slug="threads", name="Threads")
        source = SocialSource.objects.create(network=network, username="батуми торт")
        row = SocialMessage.objects.create(
            channel=source,
            external_id="1",
            url="https://www.threads.com/@a/post/1",
            sent_at="2026-11-04T08:00:00Z",
            text="бенто",
            potential_lead=True,
        )
        missing = self.client.post(
            f"/api/social/messages/{row.id}/context/",
            {"context": []},
            format="json",
        )
        self.assertEqual(missing.status_code, 403)
        response = self.client.post(
            f"/api/social/messages/{row.id}/context/",
            {
                "context": [
                    {
                        "username": "asker",
                        "text": "вопрос",
                        "sent_at": "2026-11-04T08:00:00Z",
                        "url": "https://www.threads.com/@asker/post/parent",
                    }
                ]
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(response.status_code, 204)
        row.refresh_from_db()
        self.assertEqual(row.context[0]["username"], "asker")
        self.assertEqual(row.context[0]["text"], "вопрос")
        self.assertEqual(row.context[0]["url"], "https://www.threads.com/@asker/post/parent")

    @patch("crm.telegram_views.notify_recent_leads")
    @patch("crm.telegram_views.verify_leads")
    def test_verify_leads_runs_for_network(self, verify_leads, notify_recent_leads):
        SocialNetwork.objects.create(slug="threads", name="Threads")
        response = self.client.post(
            "/api/social/networks/threads/verify-leads/",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(response.status_code, 204)
        verify_leads.assert_called_once_with("threads")
        notify_recent_leads.assert_called_once_with("threads")

    def test_verify_leads_telegram_is_rejected(self):
        response = self.client.post(
            "/api/social/networks/telegram/verify-leads/",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        self.assertEqual(response.status_code, 400)
