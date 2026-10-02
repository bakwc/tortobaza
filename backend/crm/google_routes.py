from datetime import datetime

import requests
from django.conf import settings

_ROUTE_MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
_FIELD_MASK = (
    "originIndex,destinationIndex,duration,staticDuration,distanceMeters,status,condition"
)


def compute_delivery_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    departure: datetime,
) -> tuple[int, int]:
    response = requests.post(
        _ROUTE_MATRIX_URL,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": settings.GOOGLE_ROUTES_API_KEY,
            "X-Goog-FieldMask": _FIELD_MASK,
        },
        json={
            "origins": [
                {
                    "waypoint": {
                        "location": {
                            "latLng": {
                                "latitude": origin[0],
                                "longitude": origin[1],
                            }
                        }
                    }
                }
            ],
            "destinations": [
                {
                    "waypoint": {
                        "location": {
                            "latLng": {
                                "latitude": destination[0],
                                "longitude": destination[1],
                            }
                        }
                    }
                }
            ],
            "travelMode": "DRIVE",
            "departureTime": departure.isoformat(),
            "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
        },
        timeout=20,
    )
    response.raise_for_status()
    element = response.json()[0]
    if element["condition"] != "ROUTE_EXISTS":
        raise ValueError(element["condition"])
    seconds = int(float(element["duration"].removesuffix("s")) + 0.5)
    return element["distanceMeters"], seconds
