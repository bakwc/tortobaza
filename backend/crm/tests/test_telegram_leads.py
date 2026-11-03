from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase, override_settings

from crm.models import SocialMessage, SocialNetwork, SocialSource
from crm.telegram_leads import LeadVerdict, classify_leads, notify_recent_leads


class ClassifyTelegramLeadsTests(TestCase):
    def setUp(self):
        self.channel = SocialSource.objects.create(
            network=SocialNetwork.objects.get(slug="telegram"),
            username="cakes",
        )
        self.sent_at = datetime(2026, 11, 2, 12, 0, tzinfo=dt_timezone.utc)

    def _message(self, text: str, keyword_match: bool, potential_lead: bool | None) -> SocialMessage:
        external_id = str(SocialMessage.objects.count() + 1)
        return SocialMessage.objects.create(
            channel=self.channel,
            external_id=external_id,
            url=f"https://t.me/{self.channel.username}/{external_id}",
            sent_at=self.sent_at,
            text=text,
            keyword_match=keyword_match,
            potential_lead=potential_lead,
        )

    @patch("crm.telegram_leads.OpenAI")
    def test_classifies_pending_keyword_matches(self, openai_cls):
        row = self._message("где заказать торт?", True, None)
        openai_cls.return_value.responses.parse.return_value.output_parsed = LeadVerdict(is_lead=True)
        classify_leads("telegram")
        openai_cls.return_value.responses.parse.assert_called_once()
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertEqual(call["input"], "где заказать торт?")
        self.assertNotIn("metro", call["instructions"])
        row.refresh_from_db()
        self.assertIs(row.potential_lead, True)

    @patch("crm.telegram_leads.OpenAI")
    def test_skips_already_classified_and_non_keyword(self, openai_cls):
        self._message("где заказать торт?", True, False)
        self._message("просто чат", False, None)
        classify_leads("telegram")
        openai_cls.assert_not_called()

    @patch("crm.telegram_leads.OpenAI")
    def test_empty_model_output_raises(self, openai_cls):
        self._message("торт на день рождения", True, None)
        openai_cls.return_value.responses.parse.return_value.output_parsed = None
        with self.assertRaises(RuntimeError):
            classify_leads("telegram")

    @patch("crm.telegram_leads.OpenAI")
    def test_skips_other_network(self, openai_cls):
        threads = SocialSource.objects.create(
            network=SocialNetwork.objects.create(slug="threads", name="Threads"),
            username="cakes",
        )
        row = SocialMessage.objects.create(
            channel=threads,
            external_id="1",
            url="https://www.threads.net/@cakes/post/1",
            sent_at=self.sent_at,
            text="где заказать торт?",
            keyword_match=True,
        )
        classify_leads("telegram")
        openai_cls.assert_not_called()
        row.refresh_from_db()
        self.assertIsNone(row.potential_lead)

    @patch("crm.telegram_leads.OpenAI")
    def test_threads_prompt_includes_geo_location_and_topic(self, openai_cls):
        threads = SocialSource.objects.create(
            network=SocialNetwork.objects.create(slug="threads", name="Threads"),
            username="батуми торт",
        )
        SocialMessage.objects.create(
            channel=threads,
            external_id="1",
            url="https://www.threads.com/@cakes/post/1",
            sent_at=self.sent_at,
            text="где заказать торт?",
            location="Minsk, Belarus",
            topic="торты минск",
            keyword_match=True,
        )
        openai_cls.return_value.responses.parse.return_value.output_parsed = LeadVerdict(is_lead=False)
        classify_leads("threads")
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertIn("metro", call["instructions"])
        self.assertIn("Post location: Minsk, Belarus", call["input"])
        self.assertIn("Post topic: торты минск", call["input"])
        self.assertIn("где заказать торт?", call["input"])


@override_settings(TELEGRAM_BOT_TOKEN="bot-token", TELEGRAM_LEADS_CHAT_ID="leads-chat")
class NotifyTelegramLeadsTests(TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 2, 12, 0, tzinfo=dt_timezone.utc)
        self.channel = SocialSource.objects.create(
            network=SocialNetwork.objects.get(slug="telegram"),
            username="cakes",
            title="Cakes Chat",
        )
        self.telegram_calls: list[dict] = []

    def _message(
        self,
        *,
        text: str = "где заказать торт?",
        message_id: int | None = None,
        sent_at: datetime | None = None,
        potential_lead: bool | None = True,
        lead_notified: bool = False,
    ) -> SocialMessage:
        if message_id is None:
            message_id = SocialMessage.objects.count() + 1
        if sent_at is None:
            sent_at = self.now - timedelta(hours=1)
        external_id = str(message_id)
        return SocialMessage.objects.create(
            channel=self.channel,
            external_id=external_id,
            url=f"https://t.me/{self.channel.username}/{external_id}",
            sent_at=sent_at,
            text=text,
            keyword_match=True,
            potential_lead=potential_lead,
            lead_notified=lead_notified,
        )

    def _capture_telegram(self, method: str, payload: dict) -> dict:
        self.telegram_calls.append({"method": method, "payload": payload})
        return {"ok": True, "result": {"message_id": 1}}

    @patch("crm.telegram_leads._telegram_json")
    @patch("crm.telegram_leads.timezone.now")
    def test_notifies_recent_lead_to_site_chat(self, now_mock, telegram_json):
        now_mock.return_value = self.now
        telegram_json.side_effect = self._capture_telegram
        row = self._message(message_id=15)
        notify_recent_leads("telegram")
        self.assertEqual(len(self.telegram_calls), 1)
        call = self.telegram_calls[0]
        self.assertEqual(call["method"], "sendMessage")
        self.assertEqual(call["payload"]["chat_id"], "leads-chat")
        text = call["payload"]["text"]
        self.assertIn("Cakes Chat", text)
        self.assertIn("где заказать торт?", text)
        self.assertIn("02.11.2026, 15:00", text)
        self.assertIn("https://t.me/cakes/15", text)
        self.assertEqual(call["payload"]["parse_mode"], "HTML")
        row.refresh_from_db()
        self.assertIs(row.lead_notified, True)

    @patch("crm.telegram_leads._telegram_json")
    @patch("crm.telegram_leads.timezone.now")
    def test_skips_old_non_lead_and_already_notified(self, now_mock, telegram_json):
        now_mock.return_value = self.now
        telegram_json.side_effect = self._capture_telegram
        self._message(sent_at=self.now - timedelta(hours=25))
        self._message(potential_lead=False, message_id=2)
        self._message(lead_notified=True, message_id=3)
        notify_recent_leads("telegram")
        telegram_json.assert_not_called()

    @patch("crm.telegram_leads._telegram_json")
    @patch("crm.telegram_leads.timezone.now")
    def test_no_settings_skips_send(self, now_mock, telegram_json):
        now_mock.return_value = self.now
        self._message()
        with override_settings(TELEGRAM_BOT_TOKEN="", TELEGRAM_LEADS_CHAT_ID="leads-chat"):
            notify_recent_leads("telegram")
        with override_settings(TELEGRAM_BOT_TOKEN="bot-token", TELEGRAM_LEADS_CHAT_ID=""):
            notify_recent_leads("telegram")
        telegram_json.assert_not_called()

    @patch("crm.telegram_leads._telegram_json")
    @patch("crm.telegram_leads.timezone.now")
    def test_skips_other_network(self, now_mock, telegram_json):
        now_mock.return_value = self.now
        threads = SocialSource.objects.create(
            network=SocialNetwork.objects.create(slug="threads", name="Threads"),
            username="cakes",
        )
        SocialMessage.objects.create(
            channel=threads,
            external_id="1",
            url="https://www.threads.net/@cakes/post/1",
            sent_at=self.now - timedelta(hours=1),
            text="где заказать торт?",
            keyword_match=True,
            potential_lead=True,
        )
        notify_recent_leads("telegram")
        telegram_json.assert_not_called()
