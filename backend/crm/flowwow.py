import hashlib
import hmac
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def verify_webhook_signature(body: bytes, header: str | None) -> bool:
    secret = settings.FLOWWOW_WEBHOOK_SECRET
    if not secret:
        return False
    if header is None or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(header, expected)


def log_webhook(payload: dict, body: bytes) -> None:
    order = payload.get("order") or {}
    logger.info(
        "flowwow webhook uuid=%s event=%s shopId=%s order.id=%s body=%s",
        payload.get("uuid"),
        payload.get("event"),
        payload.get("shopId"),
        order.get("id"),
        body.decode("utf-8"),
    )
