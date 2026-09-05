import json
import re
from urllib.parse import parse_qs, unquote, urlparse

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


def _google_url(lat: float, lon: float) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"


def _unwrap_instagram_url(url: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.hostname != "l.instagram.com":
        return url
    return parse_qs(parsed_url.query)["u"][0]


def _unwrap_google_consent_url(url: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.hostname != "consent.google.com":
        return url
    return parse_qs(parsed_url.query)["continue"][0]


def unwrap_maps_url(url: str) -> str:
    maps_url = _unwrap_instagram_url(url)
    if maps_url == url:
        return url
    r = requests.get(
        maps_url,
        headers=_YANDEX_FETCH_HEADERS,
        timeout=20,
        allow_redirects=True,
    )
    r.raise_for_status()
    return _unwrap_google_consent_url(r.url)


def _is_google_maps_url(url: str) -> bool:
    parsed_url = urlparse(url)
    return parsed_url.hostname in {
        "google.com",
        "www.google.com",
        "maps.google.com",
    } and parsed_url.path.startswith("/maps")


def _google_url_from_lon_lat(lon: float, lat: float) -> str | None:
    if 40 < lat < 44 and 39 < lon < 47:
        return _google_url(lat, lon)
    return None


def _parse_lon_lat_csv(value: str) -> tuple[float, float] | None:
    parts = unquote(value).split(",")
    if len(parts) < 2:
        return None
    return float(parts[0]), float(parts[1])


def _coords_from_url(url: str) -> str | None:
    query = parse_qs(urlparse(url).query)
    for key in ("pt", "ll"):
        values = query.get(key)
        if not values:
            continue
        pair = _parse_lon_lat_csv(values[0])
        if pair is None:
            continue
        google_url = _google_url_from_lon_lat(pair[0], pair[1])
        if google_url:
            return google_url
    return None


def _coords_from_state_view(html: str) -> str | None:
    match = re.search(
        r'<script type="application/json" class="state-view">(.*?)</script>',
        html,
        re.S,
    )
    if not match:
        return None
    data = json.loads(match.group(1))
    placemarks = data.get("placemarks")
    if not placemarks:
        return None
    points = placemarks.get("points")
    if not points:
        return None
    coordinates = points[0]["coordinates"]
    return _google_url_from_lon_lat(float(coordinates[0]), float(coordinates[1]))


def _coords_from_html_pt(html: str) -> str | None:
    match = re.search(r"pt=([0-9.]+(?:,|%2C)[0-9.]+)", html)
    if not match:
        return None
    pair = _parse_lon_lat_csv(match.group(1))
    if pair is None:
        return None
    return _google_url_from_lon_lat(pair[0], pair[1])


def _coords_from_html_patterns(html: str) -> str | None:
    for pattern in _COORDINATE_PATTERNS:
        match = re.search(pattern, html)
        if match:
            google_url = _google_url_from_lon_lat(
                float(match.group(1)),
                float(match.group(2)),
            )
            if google_url:
                return google_url
    return None


def yandex_url_to_google_url(yandex_url: str) -> str:
    maps_url = _unwrap_instagram_url(yandex_url)
    r = requests.get(
        maps_url,
        headers=_YANDEX_FETCH_HEADERS,
        timeout=20,
        allow_redirects=True,
    )
    r.raise_for_status()
    resolved_url = _unwrap_google_consent_url(r.url)
    if _is_google_maps_url(resolved_url):
        return resolved_url
    from_url = _coords_from_url(resolved_url)
    if from_url:
        return from_url
    from_state = _coords_from_state_view(r.text)
    if from_state:
        return from_state
    from_pt = _coords_from_html_pt(r.text)
    if from_pt:
        return from_pt
    from_html = _coords_from_html_patterns(r.text)
    if from_html:
        return from_html
    raise ValueError("Could not find coordinates in Yandex Maps response")


def resolve_google_maps_url(address: str, yandex_url: str) -> str:
    cached = cached_google_maps_url(address)
    if cached:
        return cached
    google_url = yandex_url_to_google_url(yandex_url)
    ResolvedGoogleAddress.objects.create(address=address, google_url=google_url)
    return google_url
