import io
from datetime import datetime, time
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from cart.models import Cart, CartItem, CartItemOption
from catalog.models import Category, Option, OptionGroup, Product, ProductImage
from crm.models import CrmOrder, CrmOrderImage
from crm.website import sync_website_order_status_from_crm
from orders.liberty import build_callback_check, customdata, order_amount_tetri
from orders.models import LibertyPayment, Order
from orders.services import create_order_from_cart

_TB = ZoneInfo("Asia/Tbilisi")


class WebsiteOrderCrmSyncTests(TestCase):
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
        ProductImage.objects.create(product=self.product, image=self._jpeg("cake-a.jpg"), position=0)
        ProductImage.objects.create(product=self.product, image=self._jpeg("cake-b.jpg"), position=1)
        filling = OptionGroup.objects.create(
            name="Filling",
            slug="filling",
            selection_type=OptionGroup.SELECTION_SINGLE,
        )
        self.filling_option = Option.objects.create(
            group=filling,
            name="Raspberry",
            price_delta=Decimal("0.00"),
            position=0,
        )
        self.cart = Cart.objects.create()
        item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=1, comment="write name")
        CartItemOption.objects.create(cart_item=item, option=self.filling_option)

    def _jpeg(self, name: str) -> SimpleUploadedFile:
        buf = io.BytesIO()
        im = Image.new("RGB", (40, 40), color="pink")
        im.save(buf, format="JPEG")
        return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")

    @staticmethod
    def _frozen_now() -> datetime:
        return datetime(2026, 5, 21, 10, 0, tzinfo=_TB)

    def _payload(self, payment_method: str) -> dict:
        return {
            "locale": "en",
            "fulfillment_type": Order.FULFILLMENT_DELIVERY,
            "payment_method": payment_method,
            "customer_name": "Anna",
            "customer_phone": "+995555111222",
            "customer_email": "anna@example.com",
            "customer_instagram": "@cake_lover",
            "customer_telegram": "@anna_tg",
            "comment": "no candles",
            "schedule_mode": "slot",
            "schedule_date": self._frozen_now().date(),
            "schedule_start_time": time(16, 0),
            "schedule_end_time": time(17, 0),
            "address": {
                "street": "Rustaveli",
                "building": "12",
                "apartment": "3",
                "city": "Batumi",
                "notes": "gate code 1",
            },
        }

    @patch("crm.website.schedule_crm_order_telegram_sync")
    @patch("django.utils.timezone.now")
    def test_prod_order_creates_crm_order_with_images(self, mock_now, mock_sync):
        mock_now.return_value = self._frozen_now()
        order = create_order_from_cart(self.cart, self._payload(Order.PAYMENT_CARD), Order.ENV_PROD)
        crm = CrmOrder.objects.get(website_order=order)
        self.assertEqual(crm.date.isoformat(), "2026-05-21")
        self.assertEqual(crm.time_start, time(16, 0))
        self.assertEqual(crm.time_end, time(17, 0))
        self.assertFalse(crm.when_ready)
        self.assertEqual(crm.contact, "Anna +995555111222")
        self.assertEqual(crm.nickname, "@cake_lover")
        self.assertEqual(crm.fulfillment_type, CrmOrder.FULFILLMENT_DELIVERY)
        self.assertEqual(crm.delivery_address, "Rustaveli, 12, 3, Batumi (gate code 1)")
        self.assertEqual(crm.weight, "—")
        self.assertEqual(crm.filling, "Raspberry")
        self.assertIn(f"Сайт заказ #{order.number}", crm.description)
        self.assertIn("Raspberry Dream × 1", crm.description)
        self.assertIn("Filling: Raspberry", crm.description)
        self.assertIn("write name", crm.description)
        self.assertIn("Email: anna@example.com", crm.description)
        self.assertIn("no candles", crm.description)
        self.assertEqual(crm.cake_price, Decimal("105.00"))
        self.assertEqual(crm.prepayment, Decimal("0"))
        self.assertFalse(crm.is_paid)
        self.assertEqual(crm.payment_type, CrmOrder.PAYMENT_ONLINE)
        images = list(crm.images.order_by("position"))
        self.assertEqual(len(images), 2)
        self.assertTrue(images[0].image.name.startswith("crm_orders/"))
        self.assertTrue(images[1].image.name.startswith("crm_orders/"))
        mock_sync.assert_called_once_with(crm.pk)

    @patch("crm.website.schedule_crm_order_telegram_sync")
    @patch("django.utils.timezone.now")
    def test_dev_order_does_not_create_crm_order(self, mock_now, mock_sync):
        mock_now.return_value = self._frozen_now()
        create_order_from_cart(self.cart, self._payload(Order.PAYMENT_CARD), Order.ENV_DEV)
        self.assertEqual(CrmOrder.objects.count(), 0)
        mock_sync.assert_not_called()

    @override_settings(LIBERTY_PAY_SECRET="testsecret")
    @patch("orders.views.notify_order_paid_by_card")
    @patch("crm.website.schedule_crm_order_telegram_sync")
    @patch("django.utils.timezone.now")
    def test_liberty_completed_marks_crm_paid(self, mock_now, mock_sync, mock_notify):
        mock_now.return_value = self._frozen_now()
        order = create_order_from_cart(self.cart, self._payload(Order.PAYMENT_CARD), Order.ENV_PROD)
        payment = LibertyPayment.objects.create(
            order=order,
            ordercode=f"{order.number}-abc123def456",
            amount_tetri=order_amount_tetri(order),
            testmode=False,
        )
        amount = str(payment.amount_tetri)
        customdata_value = customdata(order)
        check = build_callback_check(
            "COMPLETED",
            "tx1",
            amount,
            "GEL",
            payment.ordercode,
            "card",
            customdata_value,
            "0",
            "testsecret",
        )
        response = self.client.get(
            "/api/payments/liberty/callback/",
            {
                "status": "COMPLETED",
                "transactioncode": "tx1",
                "amount": amount,
                "currency": "GEL",
                "ordercode": payment.ordercode,
                "paymethod": "card",
                "customdata": customdata_value,
                "testmode": "0",
                "check": check,
            },
        )
        self.assertEqual(response.status_code, 200)
        crm = CrmOrder.objects.get(website_order=order)
        crm.refresh_from_db()
        self.assertTrue(crm.is_paid)
        self.assertEqual(crm.prepayment, crm.cake_price)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PAYMENT_PAID)
        mock_notify.assert_called_once_with(order.pk)
        self.assertEqual(mock_sync.call_count, 2)

    @override_settings(LIBERTY_PAY_SECRET="testsecret")
    @patch("orders.views.notify_order_paid_by_card")
    @patch("crm.website.schedule_crm_order_telegram_sync")
    @patch("django.utils.timezone.now")
    def test_duplicate_liberty_completed_does_not_create_second_crm_order(
        self, mock_now, mock_sync, mock_notify
    ):
        mock_now.return_value = self._frozen_now()
        order = create_order_from_cart(self.cart, self._payload(Order.PAYMENT_CARD), Order.ENV_PROD)
        payment = LibertyPayment.objects.create(
            order=order,
            ordercode=f"{order.number}-abc123def456",
            amount_tetri=order_amount_tetri(order),
            testmode=False,
        )
        amount = str(payment.amount_tetri)
        customdata_value = customdata(order)
        check = build_callback_check(
            "COMPLETED",
            "tx1",
            amount,
            "GEL",
            payment.ordercode,
            "card",
            customdata_value,
            "0",
            "testsecret",
        )
        payload = {
            "status": "COMPLETED",
            "transactioncode": "tx1",
            "amount": amount,
            "currency": "GEL",
            "ordercode": payment.ordercode,
            "paymethod": "card",
            "customdata": customdata_value,
            "testmode": "0",
            "check": check,
        }
        first = self.client.get("/api/payments/liberty/callback/", payload)
        second = self.client.get("/api/payments/liberty/callback/", payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(CrmOrder.objects.filter(website_order=order).count(), 1)
        self.assertEqual(CrmOrderImage.objects.filter(order__website_order=order).count(), 2)
        self.assertIn(b"Duplicate", second.content)

    @patch("crm.website.schedule_crm_order_telegram_sync")
    @patch("django.utils.timezone.now")
    def test_crm_status_maps_to_website_order_status(self, mock_now, mock_sync):
        mock_now.return_value = self._frozen_now()
        order = create_order_from_cart(self.cart, self._payload(Order.PAYMENT_CARD), Order.ENV_PROD)
        crm = CrmOrder.objects.get(website_order=order)
        cases = [
            (CrmOrder.STATUS_NEW, Order.STATUS_PENDING),
            (CrmOrder.STATUS_IN_WORK, Order.STATUS_PREPARING),
            (CrmOrder.STATUS_CLIENT_APPROVED, Order.STATUS_READY),
            (CrmOrder.STATUS_IN_DELIVERY, Order.STATUS_READY),
            (CrmOrder.STATUS_DELIVERED, Order.STATUS_DELIVERED),
        ]
        for crm_status, website_status in cases:
            crm.status = crm_status
            crm.save(update_fields=["status"])
            sync_website_order_status_from_crm(crm)
            order.refresh_from_db()
            self.assertEqual(order.status, website_status)

    @patch("crm.views.schedule_crm_order_telegram_sync")
    @patch("crm.website.schedule_crm_order_telegram_sync")
    @patch("django.utils.timezone.now")
    def test_take_in_work_sets_website_order_preparing(self, mock_now, mock_website_sync, mock_view_sync):
        mock_now.return_value = self._frozen_now()
        order = create_order_from_cart(self.cart, self._payload(Order.PAYMENT_CARD), Order.ENV_PROD)
        crm = CrmOrder.objects.get(website_order=order)
        user = User.objects.create_user(username="worker", password="password")
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f"/api/crm/orders/{crm.id}/",
            {"take_in_work": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PREPARING)

    @patch("crm.views.schedule_crm_order_telegram_sync")
    @patch("crm.website.schedule_crm_order_telegram_sync")
    @patch("django.utils.timezone.now")
    def test_patch_delivered_sets_website_order_delivered(self, mock_now, mock_website_sync, mock_view_sync):
        mock_now.return_value = self._frozen_now()
        order = create_order_from_cart(self.cart, self._payload(Order.PAYMENT_CARD), Order.ENV_PROD)
        crm = CrmOrder.objects.get(website_order=order)
        user = User.objects.create_user(username="worker", password="password")
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f"/api/crm/orders/{crm.id}/",
            {"status": CrmOrder.STATUS_DELIVERED},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_DELIVERED)

    @patch("crm.views.schedule_crm_order_telegram_sync")
    @patch("crm.website.schedule_crm_order_telegram_sync")
    @patch("django.utils.timezone.now")
    def test_status_rollback_to_new_sets_website_order_pending(self, mock_now, mock_website_sync, mock_view_sync):
        mock_now.return_value = self._frozen_now()
        order = create_order_from_cart(self.cart, self._payload(Order.PAYMENT_CARD), Order.ENV_PROD)
        crm = CrmOrder.objects.get(website_order=order)
        user = User.objects.create_user(username="worker", password="password")
        self.client.force_authenticate(user=user)
        take = self.client.patch(
            f"/api/crm/orders/{crm.id}/",
            {"take_in_work": True},
            format="json",
        )
        self.assertEqual(take.status_code, 200)
        rollback = self.client.patch(
            f"/api/crm/orders/{crm.id}/",
            {"status": CrmOrder.STATUS_NEW},
            format="json",
        )
        self.assertEqual(rollback.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PENDING)

    @patch("crm.views.schedule_crm_order_telegram_sync")
    def test_patch_status_without_website_order_succeeds(self, mock_view_sync):
        crm = CrmOrder.objects.create(
            date=self._frozen_now().date(),
            time_start=time(11, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Mango",
            cake_price=Decimal("100.00"),
            prepayment=Decimal("0.00"),
            status=CrmOrder.STATUS_NEW,
            is_paid=False,
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        user = User.objects.create_user(username="worker", password="password")
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f"/api/crm/orders/{crm.id}/",
            {"status": CrmOrder.STATUS_DELIVERED},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        crm.refresh_from_db()
        self.assertEqual(crm.status, CrmOrder.STATUS_DELIVERED)
