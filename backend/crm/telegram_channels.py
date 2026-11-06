from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from crm.models import SocialKeyword, SocialMessage, SocialSource, append_processing_event
from crm.telegram_user import _api_credentials

_HISTORY_DAYS = 30
_KEYWORD_MATCH_MAX_LENGTH = 450


def _keyword_match(text: str, keywords: list[str]) -> bool:
    if len(text) > _KEYWORD_MATCH_MAX_LENGTH:
        return False
    folded = text.casefold()
    for word in keywords:
        if word in folded:
            return True
    return False


def refresh_keyword_matches() -> None:
    keywords = [row.casefold() for row in SocialKeyword.objects.values_list("word", flat=True)]
    changed = []
    for message in SocialMessage.objects.all().only(
        "id",
        "text",
        "keyword_match",
        "processing_history",
    ).iterator():
        matched = _keyword_match(message.text, keywords)
        if message.keyword_match == matched:
            continue
        if matched:
            append_processing_event(message, {"kind": "found"})
        message.keyword_match = matched
        changed.append(message)
    if changed:
        SocialMessage.objects.bulk_update(changed, ["keyword_match", "processing_history"])


def sync_telegram_channels() -> None:
    channels = list(
        SocialSource.objects.filter(enabled=True, network__slug="telegram").order_by("id")
    )
    if not channels:
        return
    keywords = [row.casefold() for row in SocialKeyword.objects.values_list("word", flat=True)]
    api_id, api_hash = _api_credentials()
    session = settings.TELEGRAM_USER_SESSION
    if not session:
        raise RuntimeError("TELEGRAM_USER_SESSION is required")
    cutoff = timezone.now() - timedelta(days=_HISTORY_DAYS)
    with TelegramClient(StringSession(session), api_id, api_hash) as client:
        for channel in channels:
            entity = client.get_entity(channel.username)
            if channel.last_message_id == 0:
                messages = client.iter_messages(entity, offset_date=cutoff, reverse=True)
            else:
                messages = client.iter_messages(
                    entity,
                    min_id=channel.last_message_id,
                    reverse=True,
                )
            last_message_id = channel.last_message_id
            for message in messages:
                if message.id > last_message_id:
                    last_message_id = message.id
                if message.action is not None:
                    continue
                text = message.message
                if text is None:
                    text = ""
                sender_username = ""
                sender = message.sender
                if sender is not None and sender.username:
                    sender_username = sender.username
                sender_id = None
                if message.sender_id is not None:
                    sender_id = str(message.sender_id)
                matched = _keyword_match(text, keywords)
                external_id = str(message.id)
                stored = SocialMessage.objects.filter(
                    channel=channel,
                    external_id=external_id,
                ).first()
                if stored is None:
                    stored = SocialMessage(
                        channel=channel,
                        external_id=external_id,
                        sent_at=message.date,
                        text=text,
                        sender_id=sender_id,
                        sender_username=sender_username,
                        url=f"https://t.me/{channel.username}/{message.id}",
                        keyword_match=matched,
                    )
                    if matched:
                        append_processing_event(stored, {"kind": "found"})
                    stored.save()
                else:
                    stored.sent_at = message.date
                    stored.text = text
                    stored.sender_id = sender_id
                    stored.sender_username = sender_username
                    stored.url = f"https://t.me/{channel.username}/{message.id}"
                    if matched and not stored.keyword_match:
                        append_processing_event(stored, {"kind": "found"})
                    stored.keyword_match = matched
                    stored.save(
                        update_fields=[
                            "sent_at",
                            "text",
                            "sender_id",
                            "sender_username",
                            "url",
                            "keyword_match",
                            "processing_history",
                        ]
                    )
            channel.title = entity.title
            channel.telegram_id = entity.id
            channel.last_message_id = last_message_id
            channel.save(update_fields=["title", "telegram_id", "last_message_id"])
