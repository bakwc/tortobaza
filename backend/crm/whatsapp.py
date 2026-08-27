import json
import time
import urllib.request
from urllib.parse import quote

from django.conf import settings


def _request(method: str, path: str) -> dict:
    session_id = quote(settings.WHATSAPP_OWA_SESSION_ID, safe="")
    url = f"{settings.WHATSAPP_OWA_BASE_URL}/api/sessions/{session_id}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "X-API-Key": settings.WHATSAPP_OWA_API_KEY,
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_number(number: str) -> dict:
    encoded_number = quote(number, safe="")
    return _request("GET", f"/contacts/check/{encoded_number}")


def stop_session() -> dict:
    return _request("POST", "/stop")


def start_session() -> dict:
    return _request("POST", "/start")


def get_qr() -> dict:
    return _request("GET", "/qr")


def get_new_qr() -> dict:
    stop_session()
    start_session()
    time.sleep(5)
    return get_qr()
