import argparse
from urllib.parse import parse_qs, urlparse

import requests


def unwrap_google_consent_url(url: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.hostname != "consent.google.com":
        return url
    return parse_qs(parsed_url.query)["continue"][0]


def resolve_redirect_url(url: str) -> str:
    redirect_url = parse_qs(urlparse(url).query)["u"][0]
    response = requests.get(redirect_url, allow_redirects=True, timeout=20)
    response.raise_for_status()
    return unwrap_google_consent_url(response.url)


parser = argparse.ArgumentParser()
parser.add_argument("url")
args = parser.parse_args()

print(resolve_redirect_url(args.url))
