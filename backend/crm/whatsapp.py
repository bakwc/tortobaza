import json
import urllib.request
from urllib.parse import quote

from django.conf import settings


def check_number(number: str) -> dict:
    session_id = quote(settings.WHATSAPP_OWA_SESSION_ID, safe="")
    encoded_number = quote(number, safe="")
    url = f"{settings.WHATSAPP_OWA_BASE_URL}/api/sessions/{session_id}/contacts/check/{encoded_number}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "X-API-Key": settings.WHATSAPP_OWA_API_KEY,
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))
