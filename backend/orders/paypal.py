from decimal import Decimal, ROUND_HALF_UP

import requests
from django.conf import settings

from orders.models import Order, PayPalPayment


def paypal_enabled() -> bool:
    return settings.PAYPAL_ENABLED == "1"


def nbg_usd_rate() -> Decimal:
    response = requests.get(
        settings.NBG_RATES_URL,
        params={"currencies": "USD"},
        timeout=15,
    )
    response.raise_for_status()
    currency = response.json()[0]["currencies"][0]
    rate = Decimal(str(currency["rate"]))
    quantity = Decimal(str(currency["quantity"]))
    return rate / quantity


def gel_to_usd(amount: Decimal, rate: Decimal) -> Decimal:
    return (amount / rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def access_token() -> str:
    response = requests.post(
        f"{settings.PAYPAL_API_URL}/v1/oauth2/token",
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_paypal_order(payment: PayPalPayment, order: Order) -> dict:
    token = access_token()
    response = requests.post(
        f"{settings.PAYPAL_API_URL}/v2/checkout/orders",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": order.number,
                    "custom_id": str(payment.pk),
                    "description": f"Sweet Chill order #{order.number}",
                    "amount": {
                        "currency_code": payment.currency,
                        "value": format(payment.amount_usd, "f"),
                    },
                }
            ],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def capture_paypal_order(paypal_order_id: str) -> dict:
    token = access_token()
    response = requests.post(
        f"{settings.PAYPAL_API_URL}/v2/checkout/orders/{paypal_order_id}/capture",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
