from django.conf import settings
from openai import OpenAI
from pydantic import BaseModel

from crm.models import TelegramChannelMessage

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
