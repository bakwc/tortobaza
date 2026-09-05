import argparse
from urllib.parse import parse_qs, urlparse

import requests


def resolve_redirect_url(url: str) -> str:
    redirect_url = parse_qs(urlparse(url).query)["u"][0]
    response = requests.get(redirect_url, allow_redirects=True, timeout=20)
    response.raise_for_status()
    return response.url


parser = argparse.ArgumentParser()
parser.add_argument("url")
args = parser.parse_args()

print(resolve_redirect_url(args.url))
