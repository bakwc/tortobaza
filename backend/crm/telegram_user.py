import fcntl
import time
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from telethon.errors.rpcerrorlist import PhoneNotOccupiedError
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telethon.tl.functions.contacts import ResolvePhoneRequest

from crm.models import CrmOrder, ResolvedTelegramPhone

_MIN_INTERVAL_SECONDS = 3
_TB = ZoneInfo("Asia/Tbilisi")


def _api_credentials() -> tuple[int, str]:
    api_id = settings.TELEGRAM_API_ID
    api_hash = settings.TELEGRAM_API_HASH
    if not api_id or not api_hash:
        raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required")
    return int(api_id), api_hash


def _api_phone(phone: str) -> str:
    if phone.startswith("+"):
        return phone
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"+{digits}"


def _wait_rate_limit() -> None:
    state_path = settings.TELEGRAM_RESOLVE_STATE_PATH
    if not state_path:
        raise RuntimeError("TELEGRAM_RESOLVE_STATE_PATH is required")
    with Path(state_path).open("a+") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        fh.seek(0)
        raw = fh.read().strip()
        if raw:
            remaining = _MIN_INTERVAL_SECONDS - (time.time() - float(raw))
            if remaining > 0:
                time.sleep(remaining)
        fh.seek(0)
        fh.truncate()
        fh.write(str(time.time()))
        fh.flush()


def login_user() -> str:
    api_id, api_hash = _api_credentials()
    with TelegramClient(StringSession(), api_id, api_hash) as client:
        return client.session.save()


def resolve_phone(phone: str) -> dict:
    api_id, api_hash = _api_credentials()
    session = settings.TELEGRAM_USER_SESSION
    if not session:
        raise RuntimeError("TELEGRAM_USER_SESSION is required")
    _wait_rate_limit()
    with TelegramClient(StringSession(session), api_id, api_hash) as client:
        try:
            result = client(ResolvePhoneRequest(phone=_api_phone(phone)))
        except PhoneNotOccupiedError:
            return {
                "number": phone,
                "resolved": False,
                "user_id": None,
                "username": None,
            }
    user = result.users[0]
    return {
        "number": phone,
        "resolved": True,
        "user_id": user.id,
        "username": user.username,
    }


def pending_telegram_phones(limit: int) -> list[str]:
    now = timezone.now().astimezone(_TB)
    cutoff = (now - timedelta(days=1)).date()
    checked = set(ResolvedTelegramPhone.objects.values_list("number", flat=True))
    pending: list[str] = []
    seen: set[str] = set()
    orders = CrmOrder.objects.filter(deleted=False, date__gte=cutoff)
    for order in orders:
        for phone in order.phones:
            value = phone["value"]
            if not value.isdigit():
                continue
            if value in checked or value in seen:
                continue
            seen.add(value)
            pending.append(value)
            if len(pending) == limit:
                return pending
    return pending
