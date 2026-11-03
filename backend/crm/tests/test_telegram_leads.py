from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase

from crm.models import TelegramChannel, TelegramChannelMessage, TelegramKeyword
from crm.telegram_leads import LeadVerdict, classify_telegram_leads


class ClassifyTelegramLeadsTests(TestCase):
    def setUp(self):
        self.channel = TelegramChannel.objects.create(username="cakes")
        self.sent_at = datetime(2026, 11, 2, 12, 0, tzinfo=dt_timezone.utc)

    def _message(self, text: str, keyword_match: bool, potential_lead: bool | None) -> TelegramChannelMessage:
        return TelegramChannelMessage.objects.create(
            channel=self.channel,
            message_id=TelegramChannelMessage.objects.count() + 1,
            sent_at=self.sent_at,
            text=text,
            keyword_match=keyword_match,
            potential_lead=potential_lead,
        )

    @patch("crm.telegram_leads.OpenAI")
    def test_classifies_pending_keyword_matches(self, openai_cls):
        row = self._message("где заказать торт?", True, None)
        openai_cls.return_value.responses.parse.return_value.output_parsed = LeadVerdict(is_lead=True)
        classify_telegram_leads()
        openai_cls.return_value.responses.parse.assert_called_once()
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertEqual(call["input"], "где заказать торт?")
        row.refresh_from_db()
        self.assertIs(row.potential_lead, True)

    @patch("crm.telegram_leads.OpenAI")
    def test_skips_already_classified_and_non_keyword(self, openai_cls):
        self._message("где заказать торт?", True, False)
        self._message("просто чат", False, None)
        classify_telegram_leads()
        openai_cls.assert_not_called()

    @patch("crm.telegram_leads.OpenAI")
    def test_empty_model_output_raises(self, openai_cls):
        self._message("торт на день рождения", True, None)
        openai_cls.return_value.responses.parse.return_value.output_parsed = None
        with self.assertRaises(RuntimeError):
            classify_telegram_leads()
