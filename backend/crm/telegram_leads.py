from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from openai import OpenAI
from pydantic import BaseModel

from crm.models import TelegramChannelMessage
from crm.telegram import _esc, _telegram_json

LEAD_MODEL = "gpt-6.1-sol"
LEAD_TIMEOUT_SECONDS = 90

LEAD_PROMPT = """You classify Telegram chat messages for a confectionery business Sweet Chill in Batumi.

Sweet Chill sells custom cakes, bento cakes, honey cakes (medovik), macarons, cupcakes, and related desserts.

The user message is the text of one Telegram message. Decide whether the author is a potential sales lead: they are looking to buy or order confectionery (asking where to order, price, recommendations, availability, delivery, or describing what they want to order).

Return is_lead false when the product is mentioned incidentally (general chat, jokes, news, someone else's business, unrelated context) and there is no sign the author wants to buy or order from a confectionery.

Return only the structured verdict."""


class LeadVerdict(BaseModel):
    is_lead: bool


def classify_telegram_leads() -> None:
    pending = TelegramChannelMessage.objects.filter(
        keyword_match=True,
        potential_lead__isnull=True,
    ).order_by("id")
    if not pending.exists():
        return
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=LEAD_TIMEOUT_SECONDS)
    for message in pending:
        response = client.responses.parse(
            model=LEAD_MODEL,
            instructions=LEAD_PROMPT,
            input=message.text,
            text_format=LeadVerdict,
            store=False,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("Lead classification returned no data.")
        message.potential_lead = parsed.is_lead
        message.save(update_fields=["potential_lead"])


def _channel_label(channel) -> str:
    if channel.title:
        return channel.title
    return f"@{channel.username}"


def _lead_message_url(message: TelegramChannelMessage) -> str:
    return f"https://t.me/{message.channel.username}/{message.message_id}"


def build_lead_notification_html(message: TelegramChannelMessage) -> str:
    channel = message.channel
    label = _channel_label(channel)
    url = _lead_message_url(message)
    return (
        f"В канале <b>{_esc(label)}</b> спрашивают:\n"
        f"{_esc(message.text)}\n"
        f"\n"
        f'<a href="{url}">сообщение</a>'
    )


def notify_recent_telegram_leads() -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return
    cutoff = timezone.now() - timedelta(hours=24)
    pending = (
        TelegramChannelMessage.objects.filter(
            potential_lead=True,
            lead_notified=False,
            sent_at__gte=cutoff,
        )
        .select_related("channel")
        .order_by("id")
    )
    for message in pending:
        _telegram_json(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": build_lead_notification_html(message),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        message.lead_notified = True
        message.save(update_fields=["lead_notified"])
