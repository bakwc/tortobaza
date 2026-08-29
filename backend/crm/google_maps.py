import re

import requests

from crm.models import ResolvedGoogleAddress

_YANDEX_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_COORDINATE_PATTERNS = [
    r'"coordinates"\s*:\s*\[\s*'
    r"(-?\d+(?:\.\d+)?)\s*,\s*"
    r"(-?\d+(?:\.\d+)?)\s*\]",
    r'"coords"\s*:\s*\[\s*'
    r"(-?\d+(?:\.\d+)?)\s*,\s*"
    r"(-?\d+(?:\.\d+)?)\s*\]",
    r"\[\s*"
    r"(4[0-9](?:\.\d+)?)\s*,\s*"
    r"(4[0-9](?:\.\d+)?)\s*\]",
]


def cached_google_maps_url(address: str) -> str | None:
    cached = ResolvedGoogleAddress.objects.filter(address=address).first()
    if cached:
        return cached.google_url
    return None


def yandex_url_to_google_url(yandex_url: str) -> str:
    r = requests.get(
        yandex_url,
        headers=_YANDEX_FETCH_HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    html = r.text
    for pattern in _COORDINATE_PATTERNS:
        match = re.search(pattern, html)
        if match:
            a = float(match.group(1))
            b = float(match.group(2))
            lon, lat = a, b
            if 40 < lat < 44 and 39 < lon < 47:
                return (
                    "https://www.google.com/maps/search/"
                    f"?api=1&query={lat},{lon}"
                )
    raise ValueError("Could not find coordinates in Yandex Maps response")


def resolve_google_maps_url(address: str, yandex_url: str) -> str:
    cached = cached_google_maps_url(address)
    if cached:
        return cached
    google_url = yandex_url_to_google_url(yandex_url)
    ResolvedGoogleAddress.objects.create(address=address, google_url=google_url)
    return google_url
