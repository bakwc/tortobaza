from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase, override_settings

from crm.models import LeadVertical, SocialLead, SocialMessage, SocialNetwork, SocialSource
from crm.telegram_leads import LeadVerdict, classify_leads, notify_recent_leads, verify_leads


class ClassifyTelegramLeadsTests(TestCase):
    def setUp(self):
        self.channel = SocialSource.objects.create(
            network=SocialNetwork.objects.get(slug="telegram"),
            username="cakes",
        )
        self.sent_at = datetime(2026, 11, 2, 12, 0, tzinfo=dt_timezone.utc)

    def _message(
        self,
        text: str,
        keyword_match: bool,
        potential_lead: bool | None,
        lead: bool | None = None,
        vertical_slug: str = "sweet_chill",
    ) -> SocialLead:
        external_id = str(SocialMessage.objects.count() + 1)
        message = SocialMessage.objects.create(
            channel=self.channel,
            external_id=external_id,
            url=f"https://t.me/{self.channel.username}/{external_id}",
            sent_at=self.sent_at,
            text=text,
        )
        return SocialLead.objects.create(
            message=message,
            vertical=LeadVertical.objects.get(slug=vertical_slug),
            keyword_match=keyword_match,
            potential_lead=potential_lead,
            lead=lead,
        )

    @patch("crm.telegram_leads.OpenAI")
    def test_classifies_pending_keyword_matches(self, openai_cls):
        row = self._message("где заказать торт?", True, None)
        openai_cls.return_value.responses.parse.return_value.output_parsed = LeadVerdict(
            is_lead=True,
            explanation="Автор спрашивает, где заказать торт.",
        )
        classify_leads("telegram", False)
        openai_cls.return_value.responses.parse.assert_called_once()
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertEqual(call["input"], "где заказать торт?")
        self.assertNotIn("metro", call["instructions"])
        self.assertIn("one short sentence in Russian", call["instructions"])
        row.refresh_from_db()
        self.assertIs(row.potential_lead, True)
        self.assertIs(row.lead, True)
        self.assertEqual(len(row.processing_history), 1)
        event = row.processing_history[0]
        self.assertEqual(event["kind"], "classify")
        self.assertEqual(event["classifier"], "lead")
        self.assertIs(event["verdict"], True)
        self.assertEqual(event["explanation"], "Автор спрашивает, где заказать торт.")
        self.assertTrue(event["at"])

    @patch("crm.telegram_leads.OpenAI")
    def test_skips_already_classified_and_non_keyword(self, openai_cls):
        self._message("где заказать торт?", True, False)
        self._message("просто чат", False, None)
        classify_leads("telegram", False)
        openai_cls.assert_not_called()

    @patch("crm.telegram_leads.OpenAI")
    def test_empty_model_output_raises(self, openai_cls):
        self._message("торт на день рождения", True, None)
        openai_cls.return_value.responses.parse.return_value.output_parsed = None
        with self.assertRaises(RuntimeError):
            classify_leads("telegram", False)

    @patch("crm.telegram_leads.OpenAI")
    def test_skips_other_network(self, openai_cls):
        threads = SocialSource.objects.create(
            network=SocialNetwork.objects.create(slug="threads", name="Threads"),
            username="cakes",
        )
        message = SocialMessage.objects.create(
            channel=threads,
            external_id="1",
            url="https://www.threads.net/@cakes/post/1",
            sent_at=self.sent_at,
            text="где заказать торт?",
        )
        row = SocialLead.objects.create(
            message=message,
            vertical=LeadVertical.objects.get(slug="sweet_chill"),
            keyword_match=True,
        )
        classify_leads("telegram", False)
        openai_cls.assert_not_called()
        row.refresh_from_db()
        self.assertIsNone(row.potential_lead)

    @patch("crm.telegram_leads.OpenAI")
    def test_threads_prompt_includes_geo_location_and_topic(self, openai_cls):
        threads = SocialSource.objects.create(
            network=SocialNetwork.objects.create(slug="threads", name="Threads"),
            username="батуми торт",
        )
        message = SocialMessage.objects.create(
            channel=threads,
            external_id="1",
            url="https://www.threads.com/@cakes/post/1",
            sent_at=self.sent_at,
            text="где заказать торт?",
            location="Minsk, Belarus",
            topic="торты минск",
        )
        row = SocialLead.objects.create(
            message=message,
            vertical=LeadVertical.objects.get(slug="sweet_chill"),
            keyword_match=True,
        )
        openai_cls.return_value.responses.parse.return_value.output_parsed = LeadVerdict(
            is_lead=False,
            explanation="Автор ищет торт в Минске.",
        )
        classify_leads("threads", False)
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertIn("metro", call["instructions"])
        self.assertIn("Post location: Minsk, Belarus", call["input"])
        self.assertIn("Post topic: торты минск", call["input"])
        self.assertIn("где заказать торт?", call["input"])
        row.refresh_from_db()
        self.assertIs(row.potential_lead, False)
        self.assertIs(row.lead, False)
        self.assertEqual(row.processing_history[0]["classifier"], "lead")
        self.assertIs(row.processing_history[0]["verdict"], False)
        self.assertEqual(row.processing_history[0]["explanation"], "Автор ищет торт в Минске.")

    @patch("crm.telegram_leads.OpenAI")
    def test_potential_mode_leaves_lead_unset(self, openai_cls):
        threads = SocialSource.objects.create(
            network=SocialNetwork.objects.create(slug="threads", name="Threads"),
            username="батуми торт",
        )
        message = SocialMessage.objects.create(
            channel=threads,
            external_id="1",
            url="https://www.threads.com/@cakes/post/1",
            sent_at=self.sent_at,
            text="где заказать торт?",
        )
        row = SocialLead.objects.create(
            message=message,
            vertical=LeadVertical.objects.get(slug="sweet_chill"),
            keyword_match=True,
        )
        openai_cls.return_value.responses.parse.return_value.output_parsed = LeadVerdict(
            is_lead=True,
            explanation="Автор спрашивает, где заказать торт.",
        )
        classify_leads("threads", True)
        row.refresh_from_db()
        self.assertIs(row.potential_lead, True)
        self.assertIsNone(row.lead)
        self.assertEqual(row.processing_history[0]["classifier"], "lead")
        self.assertIs(row.processing_history[0]["verdict"], True)

    @patch("crm.telegram_leads.OpenAI")
    def test_verify_leads_uses_thread_context(self, openai_cls):
        threads = SocialSource.objects.create(
            network=SocialNetwork.objects.create(slug="threads", name="Threads"),
            username="батуми торт",
        )
        target = "https://www.threads.com/@cakes/post/1"
        message = SocialMessage.objects.create(
            channel=threads,
            external_id="1",
            url=target,
            sent_at=self.sent_at,
            text="Бенто тортик",
            location="Vladivostok",
            topic="",
            context=[
                {
                    "username": "asker",
                    "text": "Девушки Владивостока, что вы могли бы сделать бесплатно?",
                    "sent_at": "2026-11-04T08:00:00Z",
                    "url": "https://www.threads.com/@asker/post/parent",
                },
                {
                    "username": "cakes",
                    "text": "Бенто тортик",
                    "sent_at": "2026-11-04T08:10:00Z",
                    "url": target,
                },
            ],
            profile={
                "title": "Cakes (@cakes)",
                "description": "Владивосток",
                "posts": [
                    {
                        "text": "доставка по Владивостоку",
                        "sent_at": "2026-11-03T08:00:00Z",
                        "url": "https://www.threads.com/@cakes/post/old",
                    }
                ],
            },
        )
        row = SocialLead.objects.create(
            message=message,
            vertical=LeadVertical.objects.get(slug="sweet_chill"),
            keyword_match=True,
            potential_lead=True,
        )
        waiting = SocialMessage.objects.create(
            channel=threads,
            external_id="2",
            url="https://www.threads.com/@cakes/post/2",
            sent_at=self.sent_at,
            text="без контекста",
        )
        SocialLead.objects.create(
            message=waiting,
            vertical=LeadVertical.objects.get(slug="sweet_chill"),
            keyword_match=True,
            potential_lead=True,
        )
        openai_cls.return_value.responses.parse.return_value.output_parsed = LeadVerdict(
            is_lead=False,
            explanation="Автор во Владивостоке.",
        )
        verify_leads("threads")
        openai_cls.return_value.responses.parse.assert_called_once()
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertIn("[target]", call["instructions"])
        self.assertIn("explicit sign the author is in Batumi", call["instructions"])
        self.assertIn("Post location: Vladivostok", call["input"])
        self.assertIn("@cakes [target]", call["input"])
        self.assertIn("Девушки Владивостока", call["input"])
        self.assertIn("=== Профиль пользователя ===", call["input"])
        self.assertIn("=== Последние сообщения пользователя ===", call["input"])
        self.assertIn("доставка по Владивостоку", call["input"])
        row.refresh_from_db()
        self.assertIs(row.lead, False)
        self.assertEqual(len(row.processing_history), 1)
        event = row.processing_history[0]
        self.assertEqual(event["kind"], "classify")
        self.assertEqual(event["classifier"], "verify")
        self.assertIs(event["verdict"], False)
        self.assertEqual(event["explanation"], "Автор во Владивостоке.")

    @patch("crm.telegram_leads.OpenAI")
    def test_classifies_each_vertical_with_its_prompt(self, openai_cls):
        beauty = LeadVertical.objects.get(slug="beauty")
        beauty.prompt_classify = "BEAUTY PROMPT one short sentence in Russian"
        beauty.save(update_fields=["prompt_classify"])
        message = self._message("нужен макияж и торт", True, None).message
        SocialLead.objects.create(
            message=message,
            vertical=beauty,
            keyword_match=True,
        )
        openai_cls.return_value.responses.parse.return_value.output_parsed = LeadVerdict(
            is_lead=True,
            explanation="Подходит.",
        )
        classify_leads("telegram", False)
        instructions = [
            call.kwargs["instructions"]
            for call in openai_cls.return_value.responses.parse.call_args_list
        ]
        self.assertEqual(len(instructions), 2)
        self.assertIn("confectionery", instructions[0])
        self.assertEqual(instructions[1], "BEAUTY PROMPT one short sentence in Russian")


@override_settings(TELEGRAM_BOT_TOKEN="bot-token")
class NotifyTelegramLeadsTests(TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 2, 12, 0, tzinfo=dt_timezone.utc)
        self.channel = SocialSource.objects.create(
            network=SocialNetwork.objects.get(slug="telegram"),
            username="cakes",
            title="Cakes Chat",
        )
        sweet = LeadVertical.objects.get(slug="sweet_chill")
        sweet.telegram_chat_id = "leads-chat"
        sweet.save(update_fields=["telegram_chat_id"])
        self.telegram_calls: list[dict] = []

    def _message(
        self,
        *,
        text: str = "где заказать торт?",
        message_id: int | None = None,
        sent_at: datetime | None = None,
        potential_lead: bool | None = True,
        lead: bool | None = True,
        lead_notified: bool = False,
        vertical_slug: str = "sweet_chill",
    ) -> SocialLead:
        if message_id is None:
            message_id = SocialMessage.objects.count() + 1
        if sent_at is None:
            sent_at = self.now - timedelta(hours=1)
        external_id = str(message_id)
        message = SocialMessage.objects.create(
            channel=self.channel,
            external_id=external_id,
            url=f"https://t.me/{self.channel.username}/{external_id}",
            sent_at=sent_at,
            text=text,
        )
        return SocialLead.objects.create(
            message=message,
            vertical=LeadVertical.objects.get(slug=vertical_slug),
            keyword_match=True,
            potential_lead=potential_lead,
            lead=lead,
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
        self._message(potential_lead=False, lead=False, message_id=2)
        self._message(lead_notified=True, message_id=3)
        self._message(lead=None, message_id=4)
        notify_recent_leads("telegram")
        telegram_json.assert_not_called()

    @patch("crm.telegram_leads._telegram_json")
    @patch("crm.telegram_leads.timezone.now")
    def test_no_settings_skips_send(self, now_mock, telegram_json):
        now_mock.return_value = self.now
        self._message()
        with override_settings(TELEGRAM_BOT_TOKEN=""):
            notify_recent_leads("telegram")
        sweet = LeadVertical.objects.get(slug="sweet_chill")
        sweet.telegram_chat_id = ""
        sweet.save(update_fields=["telegram_chat_id"])
        with override_settings(TELEGRAM_BOT_TOKEN="bot-token"):
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
        message = SocialMessage.objects.create(
            channel=threads,
            external_id="1",
            url="https://www.threads.net/@cakes/post/1",
            sent_at=self.now - timedelta(hours=1),
            text="где заказать торт?",
        )
        SocialLead.objects.create(
            message=message,
            vertical=LeadVertical.objects.get(slug="sweet_chill"),
            keyword_match=True,
            potential_lead=True,
            lead=True,
        )
        notify_recent_leads("telegram")
        telegram_json.assert_not_called()

    @patch("crm.telegram_leads._telegram_json")
    @patch("crm.telegram_leads.timezone.now")
    def test_notifies_only_the_vertical_that_is_a_lead(self, now_mock, telegram_json):
        now_mock.return_value = self.now
        telegram_json.side_effect = self._capture_telegram
        beauty = LeadVertical.objects.get(slug="beauty")
        beauty.telegram_chat_id = "beauty-chat"
        beauty.save(update_fields=["telegram_chat_id"])
        row = self._message(message_id=15)
        SocialLead.objects.create(
            message=row.message,
            vertical=beauty,
            keyword_match=True,
            potential_lead=True,
            lead=False,
        )
        notify_recent_leads("telegram")
        self.assertEqual(len(self.telegram_calls), 1)
        self.assertEqual(self.telegram_calls[0]["payload"]["chat_id"], "leads-chat")
        row.refresh_from_db()
        self.assertIs(row.lead_notified, True)
        beauty_lead = SocialLead.objects.get(message=row.message, vertical=beauty)
        self.assertIs(beauty_lead.lead_notified, False)
