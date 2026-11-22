from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase

from crm.models import CrmOrder, ExchangeRateSnapshot, FinancialAccount, FinancialTransaction
from crm.paypal_order_links import sync_paypal_order_links
from orders.models import Order, PayPalPayment

_TB = ZoneInfo("Asia/Tbilisi")
CAPTURE = "9KA381818U3254813"


def _at(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, 12, 0, tzinfo=_TB)


def _account() -> FinancialAccount:
    return FinancialAccount.objects.create(
        name="PayPal",
        kind=FinancialAccount.KIND_VIRTUAL,
        currency="USD",
    )


def _order(**kwargs) -> CrmOrder:
    fields = {
        "date": date(2026, 11, 19),
        "contact": "Customer",
        "weight": "1kg",
        "filling": "Vanilla",
        "cake_price": Decimal("65.00"),
        "is_paid": True,
        "payment_type": CrmOrder.PAYMENT_PAYPAL,
    }
    fields.update(kwargs)
    return CrmOrder.objects.create(**fields)


def _created(order: CrmOrder, day: date) -> None:
    CrmOrder.objects.filter(pk=order.pk).update(created_at=_at(day))


def _income(account: FinancialAccount, amount: Decimal, tx_date: date, **kwargs) -> FinancialTransaction:
    fields = {
        "account": account,
        "date": tx_date,
        "amount": amount,
        "kind": FinancialTransaction.KIND_INCOME,
        "income_type": FinancialTransaction.INCOME_ONLINE,
        "external_id": "",
    }
    fields.update(kwargs)
    return FinancialTransaction.objects.create(**fields)


def _website() -> Order:
    return Order.objects.create(
        fulfillment_type=Order.FULFILLMENT_PICKUP,
        payment_method=Order.PAYMENT_PAYPAL,
        payment_status=Order.PAYMENT_PAID,
        customer_name="Marco",
        customer_phone="+995555000000",
        customer_email="marco@example.com",
        total=Decimal("90.00"),
    )


class SyncPaypalOrderLinksTests(TestCase):
    def test_capture_links_payment_and_fee(self):
        account = _account()
        website = _website()
        order = _order(
            payment_type=CrmOrder.PAYMENT_ONLINE,
            website_order=website,
            cake_price=Decimal("80.00"),
            delivery_price=Decimal("10.00"),
        )
        PayPalPayment.objects.create(
            order=website,
            capture_id=CAPTURE,
            amount_gel=Decimal("90.00"),
            amount_usd=Decimal("34.70"),
            exchange_rate=Decimal("2.593500"),
            status=PayPalPayment.STATUS_COMPLETED,
        )
        payment = _income(
            account,
            Decimal("34.70"),
            date(2026, 11, 13),
            external_id=f"{CAPTURE}|T0006",
        )
        fee = FinancialTransaction.objects.create(
            account=account,
            date=date(2026, 11, 13),
            amount=Decimal("-2.17"),
            kind=FinancialTransaction.KIND_EXPENSE,
            expense_type=FinancialTransaction.EXPENSE_FEES,
            external_id=f"{CAPTURE}|T0006|fee",
        )

        sync_paypal_order_links()
        sync_paypal_order_links()

        self.assertEqual(payment.crm_orders.get().pk, order.pk)
        self.assertEqual(fee.crm_orders.get().pk, order.pk)
        self.assertEqual(order.financial_transactions.count(), 2)

    def test_exact_amount_links_nine_days_before_delivery(self):
        account = _account()
        order = _order(date=date(2026, 11, 28), paypal_amount_usd=Decimal("25.07"))
        _created(order, date(2026, 10, 1))
        transaction = _income(account, Decimal("25.07"), date(2026, 11, 19))

        sync_paypal_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_three_percent_links_and_nine_percent_stays_open(self):
        account = _account()
        near = _order(date=date(2026, 11, 1), paypal_amount_usd=Decimal("100.00"))
        far = _order(date=date(2026, 11, 2), paypal_amount_usd=Decimal("200.00"))
        near_tx = _income(account, Decimal("103.00"), date(2026, 11, 1))
        far_tx = _income(account, Decimal("182.00"), date(2026, 11, 2))

        sync_paypal_order_links()

        self.assertEqual(near_tx.crm_orders.get().pk, near.pk)
        self.assertEqual(far_tx.crm_orders.count(), 0)
        self.assertEqual(far.financial_transactions.count(), 0)

    def test_gel_conversion_links_within_tolerance(self):
        account = _account()
        ExchangeRateSnapshot.objects.create(
            rates_date=date(2026, 10, 10),
            rates={"USD": "2.6005"},
        )
        order = _order(date=date(2026, 10, 11), cake_price=Decimal("177.00"))
        _created(order, date(2026, 10, 10))
        transaction = _income(
            account,
            Decimal("70.00"),
            date(2026, 10, 10),
            income_type=FinancialTransaction.INCOME_TRANSFER,
        )

        sync_paypal_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_equal_distance_to_two_orders_skips(self):
        account = _account()
        earlier = _order(date=date(2026, 11, 1), paypal_amount_usd=Decimal("25.00"))
        later = _order(date=date(2026, 11, 15), paypal_amount_usd=Decimal("25.00"))
        _created(earlier, date(2026, 1, 1))
        _created(later, date(2026, 1, 1))
        transaction = _income(account, Decimal("25.00"), date(2026, 11, 8))

        sync_paypal_order_links()

        self.assertEqual(transaction.crm_orders.count(), 0)

    def test_other_payment_type_stays_unlinked(self):
        account = _account()
        order = _order(payment_type=CrmOrder.PAYMENT_TBC, paypal_amount_usd=Decimal("50.78"))
        transaction = _income(account, Decimal("50.78"), date(2026, 11, 19))

        sync_paypal_order_links()

        self.assertEqual(transaction.crm_orders.count(), 0)
        self.assertEqual(order.financial_transactions.count(), 0)

    def test_deleted_order_stays_unlinked(self):
        account = _account()
        order = _order(deleted=True, paypal_amount_usd=Decimal("5.78"))
        transaction = _income(account, Decimal("5.78"), date(2026, 11, 19))
        website = _website()
        deleted_site = _order(
            deleted=True,
            payment_type=CrmOrder.PAYMENT_ONLINE,
            website_order=website,
        )
        PayPalPayment.objects.create(
            order=website,
            capture_id="0T407653GX653552S",
            amount_gel=Decimal("15.00"),
            amount_usd=Decimal("5.78"),
            exchange_rate=Decimal("2.597100"),
            status=PayPalPayment.STATUS_COMPLETED,
        )
        captured = _income(
            account,
            Decimal("5.78"),
            date(2026, 10, 25),
            external_id="0T407653GX653552S|T0006",
        )

        sync_paypal_order_links()

        self.assertEqual(transaction.crm_orders.count(), 0)
        self.assertEqual(captured.crm_orders.count(), 0)
        self.assertEqual(order.financial_transactions.count(), 0)
        self.assertEqual(deleted_site.financial_transactions.count(), 0)
