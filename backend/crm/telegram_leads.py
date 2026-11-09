from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from openai import OpenAI
from pydantic import BaseModel

from crm.models import SocialLead, SocialMessage, append_processing_event
from crm.telegram import _esc, _telegram_json

LEAD_MODEL = "gpt-6.1-sol"
LEAD_TIMEOUT_SECONDS = 90


class LeadVerdict(BaseModel):
    is_lead: bool
    explanation: str


def _classifier_input(message: SocialMessage) -> str:
    lines = []
    if message.location:
        lines.append(f"Post location: {message.location}")
    if message.topic:
        lines.append(f"Post topic: {message.topic}")
    if lines:
        return "\n".join(lines) + "\n\n" + message.text
    return message.text


def _verdict(client: OpenAI, instructions: str, content: str) -> LeadVerdict:
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
    return parsed


def _classify_instructions(lead: SocialLead, network_slug: str) -> str:
    instructions = lead.vertical.prompt_classify
    if network_slug != "telegram":
        instructions = instructions + lead.vertical.prompt_geo
    return instructions


def classify_leads(network_slug: str, potential: bool) -> None:
    pending = (
        SocialLead.objects.filter(
            message__channel__network__slug=network_slug,
            keyword_match=True,
            potential_lead__isnull=True,
            vertical__enabled=True,
        )
        .select_related("message", "vertical")
        .order_by("id")
    )
    if not pending.exists():
        return
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=LEAD_TIMEOUT_SECONDS)
    for lead in pending:
        verdict = _verdict(
            client,
            _classify_instructions(lead, network_slug),
            _classifier_input(lead.message),
        )
        lead.potential_lead = verdict.is_lead
        update_fields = ["potential_lead", "processing_history"]
        if not potential:
            lead.lead = verdict.is_lead
            update_fields.append("lead")
        append_processing_event(
            lead,
            {
                "kind": "classify",
                "classifier": "lead",
                "verdict": verdict.is_lead,
                "explanation": verdict.explanation,
            },
        )
        lead.save(update_fields=update_fields)


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


def _verify_instructions(lead: SocialLead) -> str:
    vertical = lead.vertical
    return (
        vertical.prompt_classify
        + vertical.prompt_geo
        + vertical.prompt_context
        + vertical.prompt_profile
    )


def verify_leads(network_slug: str) -> None:
    pending = (
        SocialLead.objects.filter(
            message__channel__network__slug=network_slug,
            potential_lead=True,
            lead__isnull=True,
            message__context__isnull=False,
            message__profile__isnull=False,
            vertical__enabled=True,
        )
        .select_related("message", "vertical")
        .order_by("id")
    )
    if not pending.exists():
        return
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=LEAD_TIMEOUT_SECONDS)
    for lead in pending:
        verdict = _verdict(client, _verify_instructions(lead), _verify_input(lead.message))
        lead.lead = verdict.is_lead
        append_processing_event(
            lead,
            {
                "kind": "classify",
                "classifier": "verify",
                "verdict": verdict.is_lead,
                "explanation": verdict.explanation,
            },
        )
        lead.save(update_fields=["lead", "processing_history"])


def _channel_label(channel) -> str:
    if channel.title:
        return channel.title
    return f"@{channel.username}"


def _lead_message_url(message: SocialMessage) -> str:
    return message.url


def _notification_intro(channel) -> str:
    slug = channel.network.slug
    if slug == "threads":
        return "В threads спрашивают:"
    if slug == "telegram":
        return f"В telegram чате <b>{_esc(_channel_label(channel))}</b> спрашивают:"
    raise RuntimeError(f"Unknown network {slug}")


def build_lead_notification_html(message: SocialMessage) -> str:
    channel = message.channel
    url = _lead_message_url(message)
    posted = timezone.localtime(message.sent_at).strftime("%d.%m.%Y, %H:%M")
    return (
        f"{_notification_intro(channel)}\n"
        f"{_esc(message.text)}\n"
        f"\n"
        f"{posted}\n"
        f'<a href="{url}">сообщение</a>'
    )


def notify_recent_leads(network_slug: str) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return
    cutoff = timezone.now() - timedelta(hours=24)
    pending = (
        SocialLead.objects.filter(
            message__channel__network__slug=network_slug,
            lead=True,
            lead_notified=False,
            message__sent_at__gte=cutoff,
            vertical__enabled=True,
        )
        .exclude(vertical__telegram_chat_id="")
        .select_related("message", "message__channel", "message__channel__network", "vertical")
        .order_by("id")
    )
    for lead in pending:
        _telegram_json(
            "sendMessage",
            {
                "chat_id": lead.vertical.telegram_chat_id,
                "text": build_lead_notification_html(lead.message),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        lead.lead_notified = True
        lead.save(update_fields=["lead_notified"])
