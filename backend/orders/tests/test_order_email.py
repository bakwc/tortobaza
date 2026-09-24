from datetime import datetime, time
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from cart.models import Cart, CartItem
from catalog.models import Category, Product
from crm.models import CrmOrder
from crm.website import mark_crm_order_paid_for_website_order
from orders.email import schedule_order_confirmed_email
from orders.models import Order
from orders.services import create_order_from_cart

_TB = ZoneInfo("Asia/Tbilisi")


class _ImmediateThread:
    def __init__(self, target, args, daemon):
        self._target = target
        self._args = args

    def start(self):
        self._target(*self._args)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
@patch("orders.email.threading.Thread", _ImmediateThread)
@patch("orders.services.send_order_notification")
@patch("crm.telegram.sync_crm_order_to_telegram")
class OrderEmailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cat = Category.objects.create(
            name="Cakes",
            slug="cakes",
            position=0,
            delivery_schedule_tier=Product.DELIVERY_SCHEDULE_SAME_DAY,
        )
        self.product = Product.objects.create(
            category=self.cat,
            name="Raspberry Dream",
            slug="raspberry-dream",
            description="",
            base_price=Decimal("100.00"),
            delivery_schedule_tier=Product.DELIVERY_SCHEDULE_SAME_DAY,
        )
        self.cart = Cart.objects.create()
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)

    @staticmethod
    def _frozen_now() -> datetime:
        return datetime(2026, 5, 21, 10, 0, tzinfo=_TB)

    def _payload(self, locale: str = "en") -> dict:
        return {
            "locale": locale,
            "fulfillment_type": Order.FULFILLMENT_DELIVERY,
            "payment_method": Order.PAYMENT_CASH,
            "customer_name": "Anna",
            "customer_phone": "+995555111222",
            "customer_email": "anna@example.com",
            "schedule_mode": "slot",
            "schedule_date": self._frozen_now().date(),
            "schedule_start_time": time(16, 0),
            "schedule_end_time": time(17, 0),
            "address": {
                "street": "Rustaveli",
                "building": "12",
                "city": "Batumi",
            },
        }

    @patch("django.utils.timezone.now")
    def test_prod_order_sends_received_email(self, mock_now, _mock_crm_tg, _mock_order_tg):
        mock_now.return_value = self._frozen_now()
        with self.captureOnCommitCallbacks(execute=True):
            order = create_order_from_cart(self.cart, self._payload(), Order.ENV_PROD)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["anna@example.com"])
        self.assertEqual(message.from_email, "info@sweet-chill.ge")
        self.assertEqual(message.subject, f"Order #{order.number} received")
        self.assertIn("not confirmed yet", message.body)
        self.assertIn("Raspberry Dream", message.body)

    @patch("django.utils.timezone.now")
    def test_received_email_uses_order_locale(self, mock_now, _mock_crm_tg, _mock_order_tg):
        mock_now.return_value = self._frozen_now()
        with self.captureOnCommitCallbacks(execute=True):
            order = create_order_from_cart(self.cart, self._payload(locale="ru"), Order.ENV_PROD)
        self.assertEqual(mail.outbox[0].subject, f"Заказ #{order.number} принят")

    @patch("django.utils.timezone.now")
    def test_dev_order_does_not_send_email(self, mock_now, _mock_crm_tg, _mock_order_tg):
        mock_now.return_value = self._frozen_now()
        with self.captureOnCommitCallbacks(execute=True):
            create_order_from_cart(self.cart, self._payload(), Order.ENV_DEV)
        self.assertEqual(mail.outbox, [])

    @patch("django.utils.timezone.now")
    def test_card_payment_sends_confirmed_email(self, mock_now, _mock_crm_tg, _mock_order_tg):
        mock_now.return_value = self._frozen_now()
        order = create_order_from_cart(self.cart, self._payload(), Order.ENV_PROD)
        with self.captureOnCommitCallbacks(execute=True):
            mark_crm_order_paid_for_website_order(order)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, f"Order #{order.number} confirmed")
        self.assertEqual(mail.outbox[0].to, ["anna@example.com"])

    @patch("django.utils.timezone.now")
    def test_manager_confirm_sends_confirmed_email_once(self, mock_now, _mock_crm_tg, _mock_order_tg):
        mock_now.return_value = self._frozen_now()
        order = create_order_from_cart(self.cart, self._payload(), Order.ENV_PROD)
        crm = CrmOrder.objects.get(website_order=order)
        user = User.objects.create_user(username="worker", password="password")
        self.client.force_authenticate(user=user)
        with self.captureOnCommitCallbacks(execute=True):
            first = self.client.patch(
                f"/api/crm/orders/{crm.id}/",
                {"status": CrmOrder.STATUS_NEW},
                format="json",
            )
            second = self.client.patch(
                f"/api/crm/orders/{crm.id}/",
                {"status": CrmOrder.STATUS_NEW},
                format="json",
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, f"Order #{order.number} confirmed")

    def test_non_website_order_does_not_send_email(self, _mock_crm_tg, _mock_order_tg):
        crm = CrmOrder.objects.create(
            date=self._frozen_now().date(),
            time_start=time(16, 0),
            contact="Customer",
            weight="1kg",
            filling="Vanilla",
            cake_price=Decimal("50.00"),
            status=CrmOrder.STATUS_NEW,
        )
        with self.captureOnCommitCallbacks(execute=True):
            schedule_order_confirmed_email(crm, CrmOrder.STATUS_UNCONFIRMED)
        self.assertEqual(mail.outbox, [])

    @patch("django.utils.timezone.now")
    def test_create_order_without_email_is_rejected(self, mock_now, _mock_crm_tg, _mock_order_tg):
        mock_now.return_value = self._frozen_now()
        payload = self._payload()
        del payload["customer_email"]
        response = self.client.post(
            "/api/orders/",
            payload,
            format="json",
            HTTP_X_CART_TOKEN=str(self.cart.token),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("customer_email", response.json())
