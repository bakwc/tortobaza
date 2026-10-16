import argparse

import requests

parser = argparse.ArgumentParser()
parser.add_argument("apikey")
parser.add_argument("origin")
parser.add_argument("destination")
args = parser.parse_args()

response = requests.get(
    "https://api.routing.yandex.net/v2/distancematrix",
    params={
        "apikey": args.apikey,
        "origins": args.origin,
        "destinations": args.destination,
    },
)
response.raise_for_status()
print(response.json()["rows"][0]["elements"][0]["distance"]["value"])
