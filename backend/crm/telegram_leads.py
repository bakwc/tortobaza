from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from openai import OpenAI
from pydantic import BaseModel

from crm.models import SocialMessage
from crm.telegram import _esc, _telegram_json

LEAD_MODEL = "gpt-6.1-sol"
LEAD_TIMEOUT_SECONDS = 90

LEAD_PROMPT = """You classify Telegram chat messages for a confectionery business Sweet Chill in Batumi.

Sweet Chill sells custom cakes, bento cakes, honey cakes (medovik), macarons, cupcakes, and related desserts.

The user message is the text of one Telegram message. Decide whether the author is a potential sales lead: they are looking to buy or order confectionery (asking where to order, price, recommendations, availability, delivery, or describing what they want to order).

Return is_lead false when the product is mentioned incidentally (general chat, jokes, news, someone else's business, unrelated context) and there is no sign the author wants to buy or order from a confectionery.

Return only the structured verdict."""

LEAD_GEO_PROMPT = """

The business only delivers in Batumi and Georgia. Return is_lead false when the author is clearly looking for a confectionery in another city or country, or mentions a metro station, a district, or a street that is not in Batumi. Batumi has no metro. If no location is mentioned, decide as usual.

The user message may start with "Post location: ..." and "Post topic: ...". A location or a topic that names another city or country means is_lead false. Batumi or Georgia means the geography fits. A topic may be unrelated to a place, for example "Cooking Threads"; ignore such a topic."""

LEAD_CONTEXT_PROMPT = """

The user message is a thread of posts. The target post is marked with [target]. The other posts are the conversation around it: the post it replies to and the replies under it.

Return is_lead false when the target post answers a question about another city or country, or about something unrelated to buying confectionery in Batumi. A reply that offers cakes only because someone asked what they could do for free, or that answers a request for another city, is not a lead."""

LEAD_PROFILE_PROMPT = """

The user message also contains the author's profile and their recent posts, under "=== Профиль пользователя ===" and "=== Последние сообщения пользователя ===".

Decide the author's city from the post location, the post topic, the thread, the profile, and the recent posts. Return is_lead true only when there is an explicit sign the author is in Batumi. Return is_lead false when another city is indicated, including other cities in Georgia, or when the city cannot be determined."""


class LeadVerdict(BaseModel):
    is_lead: bool


def _classifier_input(message: SocialMessage) -> str:
    lines = []
    if message.location:
        lines.append(f"Post location: {message.location}")
    if message.topic:
        lines.append(f"Post topic: {message.topic}")
    if lines:
        return "\n".join(lines) + "\n\n" + message.text
    return message.text


def _verdict(client: OpenAI, instructions: str, content: str) -> bool:
    response = client.responses.parse(
        model=LEAD_MODEL,
        instructions=instructions,
        input=content,
        text_format=LeadVerdict,
        store=False,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("Lead classification returned no data.")
    return parsed.is_lead


def classify_leads(network_slug: str, potential: bool) -> None:
    pending = SocialMessage.objects.filter(
        channel__network__slug=network_slug,
        keyword_match=True,
        potential_lead__isnull=True,
    ).order_by("id")
    if not pending.exists():
        return
    instructions = LEAD_PROMPT
    if network_slug != "telegram":
        instructions = LEAD_PROMPT + LEAD_GEO_PROMPT
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=LEAD_TIMEOUT_SECONDS)
    for message in pending:
        is_lead = _verdict(client, instructions, _classifier_input(message))
        message.potential_lead = is_lead
        update_fields = ["potential_lead"]
        if not potential:
            message.lead = is_lead
            update_fields.append("lead")
        message.save(update_fields=update_fields)


def _verify_input(message: SocialMessage) -> str:
    lines = []
    if message.location:
        lines.append(f"Post location: {message.location}")
    if message.topic:
        lines.append(f"Post topic: {message.topic}")
    lines.append("Thread:")
    for post in message.context:
        marker = ""
        if post["url"] == message.url:
            marker = " [target]"
        lines.append(f"@{post['username']}{marker}")
        lines.append(post["text"])
        lines.append(str(post["sent_at"]))
        lines.append(post["url"])
        lines.append("")
    profile = message.profile
    lines.append("=== Профиль пользователя ===")
    lines.append(profile["title"])
    lines.append(profile["description"])
    lines.append("")
    lines.append("=== Последние сообщения пользователя ===")
    for post in profile["posts"]:
        lines.append(post["text"])
        lines.append(str(post["sent_at"]))
        lines.append(post["url"])
        lines.append("")
    return "\n".join(lines).strip()


def verify_leads(network_slug: str) -> None:
    pending = SocialMessage.objects.filter(
        channel__network__slug=network_slug,
        potential_lead=True,
        lead__isnull=True,
        context__isnull=False,
        profile__isnull=False,
    ).order_by("id")
    if not pending.exists():
        return
    instructions = LEAD_PROMPT + LEAD_GEO_PROMPT + LEAD_CONTEXT_PROMPT + LEAD_PROFILE_PROMPT
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=LEAD_TIMEOUT_SECONDS)
    for message in pending:
        message.lead = _verdict(client, instructions, _verify_input(message))
        message.save(update_fields=["lead"])


def _channel_label(channel) -> str:
    if channel.title:
        return channel.title
    return f"@{channel.username}"


def _lead_message_url(message: SocialMessage) -> str:
    return message.url


def build_lead_notification_html(message: SocialMessage) -> str:
    channel = message.channel
    label = _channel_label(channel)
    url = _lead_message_url(message)
    posted = timezone.localtime(message.sent_at).strftime("%d.%m.%Y, %H:%M")
    return (
        f"В канале <b>{_esc(label)}</b> спрашивают:\n"
        f"{_esc(message.text)}\n"
        f"\n"
        f"{posted}\n"
        f'<a href="{url}">сообщение</a>'
    )


def notify_recent_leads(network_slug: str) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_LEADS_CHAT_ID
    if not token or not chat_id:
        return
    cutoff = timezone.now() - timedelta(hours=24)
    pending = (
        SocialMessage.objects.filter(
            channel__network__slug=network_slug,
            lead=True,
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
