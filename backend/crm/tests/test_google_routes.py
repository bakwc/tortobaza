from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings

from crm.google_routes import compute_delivery_route

_TB = ZoneInfo("Asia/Tbilisi")


def _response(payload: list) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload
    return response


@override_settings(GOOGLE_ROUTES_API_KEY="route-key")
class ComputeDeliveryRouteTests(TestCase):
    @patch("crm.google_routes.requests.post")
    def test_posts_matrix_and_parses_duration(self, post):
        post.return_value = _response(
            [
                {
                    "originIndex": 0,
                    "destinationIndex": 0,
                    "status": {},
                    "condition": "ROUTE_EXISTS",
                    "distanceMeters": 4200,
                    "duration": "165s",
                    "staticDuration": "150s",
                }
            ]
        )
        departure = datetime(2026, 10, 3, 18, 30, tzinfo=_TB)
        distance, seconds = compute_delivery_route(
            (41.6168, 41.6367),
            (41.64, 41.65),
            departure,
        )
        self.assertEqual((distance, seconds), (4200, 165))
        post.assert_called_once_with(
            "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": "route-key",
                "X-Goog-FieldMask": (
                    "originIndex,destinationIndex,duration,staticDuration,"
                    "distanceMeters,status,condition"
                ),
            },
            json={
                "origins": [
                    {
                        "waypoint": {
                            "location": {
                                "latLng": {
                                    "latitude": 41.6168,
                                    "longitude": 41.6367,
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
                                    "latitude": 41.64,
                                    "longitude": 41.65,
                                }
                            }
                        }
                    }
                ],
                "travelMode": "DRIVE",
                "departureTime": "2026-10-03T18:30:00+04:00",
                "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
            },
            timeout=20,
        )

    @patch("crm.google_routes.requests.post")
    def test_rounds_fractional_duration(self, post):
        post.return_value = _response(
            [
                {
                    "condition": "ROUTE_EXISTS",
                    "distanceMeters": 800,
                    "duration": "90.6s",
                }
            ]
        )
        distance, seconds = compute_delivery_route(
            (41.6168, 41.6367),
            (41.64, 41.65),
            datetime(2026, 10, 3, 18, 30, tzinfo=_TB),
        )
        self.assertEqual((distance, seconds), (800, 91))

    @patch("crm.google_routes.requests.post")
    def test_missing_route_raises(self, post):
        post.return_value = _response([{"condition": "ROUTE_NOT_FOUND"}])
        with self.assertRaises(ValueError):
            compute_delivery_route(
                (41.6168, 41.6367),
                (41.64, 41.65),
                datetime(2026, 10, 3, 18, 30, tzinfo=_TB),
            )
