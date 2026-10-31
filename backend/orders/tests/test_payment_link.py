from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from django.test import TestCase, override_settings

from orders.paypal import create_payment_link


def _token_response() -> Mock:
    response = Mock()
    response.ok = True
    response.json.return_value = {"access_token": "token"}
    return response


def _link_response() -> Mock:
    response = Mock()
    response.ok = True
    response.json.return_value = {
        "id": "PLB-TEST",
        "links": [
            {
                "rel": "payment_link",
                "href": "https://www.paypal.com/ncp/payment/PLB-TEST",
            }
        ],
    }
    return response


@override_settings(
    PAYPAL_API_URL="https://api-m.paypal.com",
    PAYPAL_CLIENT_ID="id",
    PAYPAL_CLIENT_SECRET="secret",
)
class PaymentLinkRetryTests(TestCase):
    def test_post_retries_then_succeeds(self):
        resource_calls = {"count": 0}

        def post(url, **kwargs):
            if url.endswith("/v1/oauth2/token"):
                return _token_response()
            resource_calls["count"] += 1
            if resource_calls["count"] == 1:
                raise requests.ConnectionError("aborted")
            return _link_response()

        with (
            patch("orders.paypal.requests.post", side_effect=post),
            patch("orders.paypal.time.sleep") as sleep,
        ):
            link_id, url = create_payment_link(350, Decimal("50.78"), "https://sweet-chill.ge")
        self.assertEqual(link_id, "PLB-TEST")
        self.assertEqual(url, "https://www.paypal.com/ncp/payment/PLB-TEST")
        self.assertEqual(resource_calls["count"], 2)
        sleep.assert_called_once()

    def test_post_raises_after_five_connection_errors(self):
        def post(url, **kwargs):
            if url.endswith("/v1/oauth2/token"):
                return _token_response()
            raise requests.ConnectionError("aborted")

        with (
            patch("orders.paypal.requests.post", side_effect=post) as post_mock,
            patch("orders.paypal.time.sleep") as sleep,
        ):
            with self.assertRaises(requests.ConnectionError):
                create_payment_link(350, Decimal("50.78"), "https://sweet-chill.ge")
        resource_calls = [
            call
            for call in post_mock.call_args_list
            if str(call.args[0]).endswith("/v1/checkout/payment-resources")
        ]
        self.assertEqual(len(resource_calls), 5)
        self.assertEqual(sleep.call_count, 4)
