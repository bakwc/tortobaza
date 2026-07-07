import hashlib
import xml.sax.saxutils

from django.conf import settings

from orders.models import LibertyPayment, Order


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def order_amount_tetri(order: Order) -> int:
    return int(order.total * 100)


def pay_lng(order: Order) -> str:
    if order.locale == "ka":
        return "KA"
    return "EN"


def customdata(order: Order) -> str:
    return f"{order.number}|{order.lookup_token}"


def build_start_check(
    merchant: str,
    ordercode: str,
    amount: str,
    currency: str,
    description: str,
    clientname: str,
    customdata_value: str,
    lng: str,
    testmode: str,
    secret: str,
) -> str:
    payload = (
        secret
        + merchant
        + ordercode
        + amount
        + currency
        + description
        + clientname
        + customdata_value
        + lng
        + testmode
    )
    return sha256_hex(payload)


def build_callback_check(
    status: str,
    transactioncode: str,
    amount: str,
    currency: str,
    ordercode: str,
    paymethod: str,
    customdata_value: str,
    testmode: str,
    secret: str,
) -> str:
    payload = (
        status
        + transactioncode
        + amount
        + currency
        + ordercode
        + paymethod
        + customdata_value
        + testmode
        + secret
    )
    return sha256_hex(payload)


def build_response_check(resultcode: str, resultdesc: str, transactioncode: str, secret: str) -> str:
    return sha256_hex(resultcode + resultdesc + transactioncode + secret)


def build_start_fields(payment: LibertyPayment, order: Order) -> dict[str, str]:
    merchant = settings.LIBERTY_PAY_MERCHANT
    secret = settings.LIBERTY_PAY_SECRET
    amount = str(payment.amount_tetri)
    currency = payment.currency
    description = f"Sweet Chill order #{order.number}"
    clientname = order.customer_name
    customdata_value = customdata(order)
    lng = pay_lng(order)
    testmode = "1" if payment.testmode else "0"
    check = build_start_check(
        merchant,
        payment.ordercode,
        amount,
        currency,
        description,
        clientname,
        customdata_value,
        lng,
        testmode,
        secret,
    )
    return {
        "merchant": merchant,
        "ordercode": payment.ordercode,
        "amount": amount,
        "currency": currency,
        "description": description,
        "clientname": clientname,
        "customdata": customdata_value,
        "lng": lng,
        "testmode": testmode,
        "check": check,
    }


def callback_response_xml(resultcode: str, resultdesc: str, transactioncode: str) -> str:
    secret = settings.LIBERTY_PAY_SECRET
    check = build_response_check(resultcode, resultdesc, transactioncode, secret)
    return (
        "<result>"
        f"<resultcode>{xml.sax.saxutils.escape(resultcode)}</resultcode>"
        f"<resultdesc>{xml.sax.saxutils.escape(resultdesc)}</resultdesc>"
        f"<check>{check}</check>"
        "<data></data>"
        "</result>"
    )
