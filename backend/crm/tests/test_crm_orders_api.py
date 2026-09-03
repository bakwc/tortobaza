import io
from datetime import date, time
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import UserProfile
from crm.models import CrmOrder, CrmOrderImage, ResolvedGoogleAddress

_TB = ZoneInfo("Asia/Tbilisi")


class CrmOrdersApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="worker", password="password")
        self.admin = User.objects.create_user(username="admin", password="password", is_staff=True)

    def test_unauthenticated_access_denied(self):
        response = self.client.get("/api/crm/orders/")
        self.assertEqual(response.status_code, 403)

        patch_response = self.client.patch("/api/crm/orders/1/", {"status": CrmOrder.STATUS_DELIVERED})
        self.assertEqual(patch_response.status_code, 403)

        post_response = self.client.post("/api/crm/orders/", {})
        self.assertEqual(post_response.status_code, 403)

        get_detail = self.client.get("/api/crm/orders/1/")
        self.assertEqual(get_detail.status_code, 403)

        put_response = self.client.put("/api/crm/orders/1/", {})
        self.assertEqual(put_response.status_code, 403)

        delete_response = self.client.delete("/api/crm/orders/1/")
        self.assertEqual(delete_response.status_code, 403)

    def test_get_orders_default_today_tbilisi(self):
        today = timezone.now().astimezone(_TB).date()
        yesterday = date(today.year, today.month, today.day - 1) if today.day > 1 else date(today.year, today.month - 1, 28)

        today_order = CrmOrder.objects.create(
            date=today,
            time_start=time(12, 0),
            contact="+995555111222",
            nickname="@cake_lover",
            delivery_address="Rustaveli 12, Batumi",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla Strawberry",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            is_paid=False,
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        CrmOrder.objects.create(
            date=yesterday,
            time_start=time(14, 0),
            contact="+995555333444",
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            weight="1kg",
            filling="Chocolate",
            cake_price=Decimal("70.00"),
            prepayment=Decimal("70.00"),
            is_paid=True,
            payment_type=CrmOrder.PAYMENT_TBC,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/crm/orders/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["date"], today.isoformat())
        self.assertEqual(len(data["orders"]), 1)
        self.assertEqual(data["orders"][0]["id"], today_order.id)
        self.assertEqual(data["orders"][0]["contact"], "+995555111222")
        self.assertEqual(data["orders"][0]["contact_tel"], "tel:+995555111222")
        self.assertEqual(data["orders"][0]["contact_whatsapp"], "https://wa.me/995555111222")
        self.assertEqual(data["orders"][0]["contact_telegram"], "https://t.me/+995555111222")
        self.assertEqual(data["orders"][0]["nickname"], "@cake_lover")
        self.assertEqual(data["orders"][0]["delivery_address"], "Rustaveli 12, Batumi")

    def test_get_orders_by_date_and_ordering(self):
        target_date = date(2026, 8, 25)
        order_late = CrmOrder.objects.create(
            date=target_date,
            time_start=time(16, 30),
            time_end=time(18, 0),
            contact="Late Order",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="3kg",
            filling="Red Velvet",
            cake_price=Decimal("150.00"),
            prepayment=Decimal("50.00"),
            is_paid=False,
            payment_type=CrmOrder.PAYMENT_BOG,
        )
        order_early = CrmOrder.objects.create(
            date=target_date,
            time_start=time(10, 0),
            contact="Early Order",
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            weight="1.5kg",
            filling="Snickers",
            cake_price=Decimal("90.00"),
            prepayment=Decimal("90.00"),
            is_paid=True,
            payment_type=CrmOrder.PAYMENT_TERMINAL,
        )

        dummy_file = SimpleUploadedFile("sample.jpg", b"dummy content", content_type="image/jpeg")
        CrmOrderImage.objects.create(order=order_early, image=dummy_file, position=0)

        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/crm/orders/", {"date": "2026-08-25"})
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["date"], "2026-08-25")
        self.assertEqual(len(data["orders"]), 2)
        self.assertEqual(data["orders"][0]["id"], order_early.id)
        self.assertEqual(data["orders"][0]["time_start"], "10:00:00")
        self.assertIsNone(data["orders"][0]["time_end"])
        self.assertEqual(len(data["orders"][0]["images"]), 1)
        self.assertIn("src", data["orders"][0]["images"][0]["image"])
        self.assertIn("srcset", data["orders"][0]["images"][0]["image"])

        self.assertEqual(data["orders"][1]["id"], order_late.id)
        self.assertEqual(data["orders"][1]["time_start"], "16:30:00")
        self.assertEqual(data["orders"][1]["time_end"], "18:00:00")

    def test_midnight_orders_sort_last(self):
        target_date = date(2026, 8, 25)
        midnight = CrmOrder.objects.create(
            date=target_date,
            time_start=time(0, 0),
            contact="Midnight",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("100.00"),
            prepayment=Decimal("0.00"),
            is_paid=False,
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        evening = CrmOrder.objects.create(
            date=target_date,
            time_start=time(23, 0),
            contact="Evening",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("100.00"),
            prepayment=Decimal("0.00"),
            is_paid=False,
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        morning = CrmOrder.objects.create(
            date=target_date,
            time_start=time(10, 0),
            contact="Morning",
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            weight="1kg",
            filling="Chocolate",
            cake_price=Decimal("80.00"),
            prepayment=Decimal("0.00"),
            is_paid=False,
            payment_type=CrmOrder.PAYMENT_CASH,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/crm/orders/", {"date": "2026-08-25"})
        self.assertEqual(response.status_code, 200)
        ids = [order["id"] for order in response.json()["orders"]]
        self.assertEqual(ids, [morning.id, evening.id, midnight.id])

        month_response = self.client.get("/api/crm/orders/", {"month": "2026-08"})
        self.assertEqual(month_response.status_code, 200)
        month_ids = [order["id"] for order in month_response.json()["orders"]]
        self.assertEqual(month_ids, [morning.id, evening.id, midnight.id])

    def test_get_orders_by_month_and_ordering(self):
        in_month_late_day = CrmOrder.objects.create(
            date=date(2026, 8, 28),
            time_start=time(9, 0),
            contact="August 28",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("110.00"),
            prepayment=Decimal("10.00"),
            is_paid=False,
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        in_month_early_day = CrmOrder.objects.create(
            date=date(2026, 8, 3),
            time_start=time(18, 0),
            contact="August 3",
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            weight="1kg",
            filling="Chocolate",
            cake_price=Decimal("80.00"),
            prepayment=Decimal("80.00"),
            is_paid=True,
            payment_type=CrmOrder.PAYMENT_TBC,
        )
        CrmOrder.objects.create(
            date=date(2026, 7, 31),
            time_start=time(12, 0),
            contact="July",
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            weight="1kg",
            filling="Honey",
            cake_price=Decimal("50.00"),
            prepayment=Decimal("0.00"),
            is_paid=False,
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        CrmOrder.objects.create(
            date=date(2026, 9, 1),
            time_start=time(12, 0),
            contact="September",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="1kg",
            filling="Honey",
            cake_price=Decimal("50.00"),
            prepayment=Decimal("0.00"),
            is_paid=False,
            payment_type=CrmOrder.PAYMENT_CASH,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/crm/orders/", {"month": "2026-08"})
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["month"], "2026-08")
        self.assertNotIn("date", data)
        self.assertEqual(len(data["orders"]), 2)
        self.assertEqual(data["orders"][0]["id"], in_month_early_day.id)
        self.assertEqual(data["orders"][1]["id"], in_month_late_day.id)

    def test_get_orders_rejects_date_and_month_together(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/crm/orders/", {"date": "2026-08-25", "month": "2026-08"})
        self.assertEqual(response.status_code, 400)

    def test_patch_order_status(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 25),
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

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_DELIVERED},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_DELIVERED)
        self.assertFalse(order.is_paid)
        self.assertEqual(order.weight, "2kg")

    def test_regular_user_can_take_in_work_with_telegram_nick(self):
        UserProfile.objects.create(user=self.user, telegram_username="chef_anna")
        order = CrmOrder.objects.create(
            date=date(2026, 8, 25),
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
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"take_in_work": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["taken_by_name"], "chef_anna")
        self.assertEqual(data["taken_by_telegram_url"], "https://t.me/chef_anna")
        self.assertEqual(data["status"], CrmOrder.STATUS_IN_WORK)
        order.refresh_from_db()
        self.assertEqual(order.taken_by_id, self.user.id)
        self.assertEqual(order.status, CrmOrder.STATUS_IN_WORK)

    def test_take_in_work_reassigns_to_other_user(self):
        UserProfile.objects.create(user=self.user, telegram_username="chef_one")
        other = User.objects.create_user(username="other", password="password")
        UserProfile.objects.create(user=other, telegram_username="chef_two")
        order = CrmOrder.objects.create(
            date=date(2026, 8, 25),
            time_start=time(11, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Mango",
            cake_price=Decimal("100.00"),
            prepayment=Decimal("0.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
            status=CrmOrder.STATUS_IN_WORK,
            taken_by=self.user,
        )
        self.client.force_authenticate(user=other)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"take_in_work": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["taken_by_name"], "chef_two")
        self.assertEqual(data["taken_by_telegram_url"], "https://t.me/chef_two")
        order.refresh_from_db()
        self.assertEqual(order.taken_by_id, other.id)
        self.assertEqual(order.status, CrmOrder.STATUS_IN_WORK)

    def test_take_in_work_falls_back_to_site_username(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 25),
            time_start=time(11, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Mango",
            cake_price=Decimal("100.00"),
            prepayment=Decimal("0.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"take_in_work": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["taken_by_name"], "worker")
        self.assertIsNone(data["taken_by_telegram_url"])
        order.refresh_from_db()
        self.assertEqual(order.taken_by_id, self.user.id)

    def test_take_in_work_does_not_rollback_later_status(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 25),
            time_start=time(11, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Mango",
            cake_price=Decimal("100.00"),
            prepayment=Decimal("0.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
            status=CrmOrder.STATUS_CLIENT_APPROVED,
            taken_by=self.user,
        )
        other = User.objects.create_user(username="other", password="password")
        self.client.force_authenticate(user=other)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"take_in_work": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_CLIENT_APPROVED)
        self.assertEqual(order.taken_by_id, other.id)

    def test_patch_status_new_clears_taken_by(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 25),
            time_start=time(11, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Mango",
            cake_price=Decimal("100.00"),
            prepayment=Decimal("0.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
            status=CrmOrder.STATUS_IN_WORK,
            taken_by=self.user,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_NEW},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_NEW)
        self.assertIsNone(order.taken_by_id)

    def test_patch_status_in_work_assigns_current_user_when_empty(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 25),
            time_start=time(11, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Mango",
            cake_price=Decimal("100.00"),
            prepayment=Decimal("0.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
            status=CrmOrder.STATUS_NEW,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_IN_WORK},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_IN_WORK)
        self.assertEqual(order.taken_by_id, self.user.id)

    def test_invalid_date_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/crm/orders/", {"date": "invalid-date"})
        self.assertEqual(response.status_code, 400)

    def test_scaled_crm_order_image(self):
        buf = io.BytesIO()
        im = Image.new("RGB", (100, 100), color="pink")
        im.save(buf, format="JPEG")
        image_file = SimpleUploadedFile("test_cake.jpg", buf.getvalue(), content_type="image/jpeg")

        order = CrmOrder.objects.create(
            date=date(2026, 8, 25),
            time_start=time(10, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            weight="1kg",
            filling="Vanilla",
            cake_price=Decimal("50.00"),
            prepayment=Decimal("50.00"),
            is_paid=True,
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        crm_img = CrmOrderImage.objects.create(order=order, image=image_file, position=0)

        response = self.client.get(f"/api/img/{crm_img.image.name}?w=600")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/webp")

    def _jpeg(self, name: str) -> SimpleUploadedFile:
        buf = io.BytesIO()
        im = Image.new("RGB", (40, 40), color="pink")
        im.save(buf, format="JPEG")
        return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")

    def _order_payload(self, **overrides):
        payload = {
            "date": "2026-08-26",
            "time_start": "12:00:00",
            "contact": "Customer",
            "nickname": "@nick",
            "delivery_address": "Rustaveli 1",
            "fulfillment_type": CrmOrder.FULFILLMENT_DELIVERY,
            "status": CrmOrder.STATUS_NEW,
            "weight": "2kg",
            "filling": "Vanilla",
            "description": "Note",
            "cake_price": "120.00",
            "prepayment": "30.00",
            "is_paid": False,
            "payment_type": CrmOrder.PAYMENT_CASH,
        }
        payload.update(overrides)
        return payload

    def test_regular_user_cannot_create_or_edit_order(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 26),
            time_start=time(12, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            is_paid=False,
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        self.client.force_authenticate(user=self.user)
        detail_url = f"/api/crm/orders/{order.id}/"

        post_response = self.client.post("/api/crm/orders/", self._order_payload(), format="multipart")
        self.assertEqual(post_response.status_code, 403)

        put_response = self.client.put(detail_url, self._order_payload(), format="multipart")
        self.assertEqual(put_response.status_code, 403)

        paid_response = self.client.patch(detail_url, {"is_paid": True}, format="json")
        self.assertEqual(paid_response.status_code, 403)

        mixed_response = self.client.patch(
            detail_url,
            {"status": CrmOrder.STATUS_DELIVERED, "is_paid": True},
            format="json",
        )
        self.assertEqual(mixed_response.status_code, 403)

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, 403)

        order.refresh_from_db()
        self.assertFalse(order.deleted)
        self.assertFalse(order.is_paid)
        self.assertEqual(order.status, CrmOrder.STATUS_NEW)
        self.assertEqual(CrmOrder.objects.filter(deleted=False).count(), 1)

    def test_admin_can_patch_is_paid(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 25),
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
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_DELIVERED, "is_paid": True, "weight": "99kg"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_DELIVERED)
        self.assertTrue(order.is_paid)
        self.assertEqual(order.weight, "2kg")

    def test_create_order(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post("/api/crm/orders/", self._order_payload(), format="multipart")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["contact"], "Customer")
        self.assertIsNone(data["contact_tel"])
        self.assertIsNone(data["contact_whatsapp"])
        self.assertIsNone(data["contact_telegram"])
        self.assertEqual(data["date"], "2026-08-26")
        self.assertEqual(data["time_start"], "12:00:00")
        self.assertEqual(data["nickname"], "@nick")
        self.assertEqual(len(data["images"]), 0)
        self.assertTrue(CrmOrder.objects.filter(pk=data["id"]).exists())

    def test_create_order_with_unknown_time(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/crm/orders/",
            self._order_payload(time_start="", time_end=""),
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIsNone(data["time_start"])
        self.assertIsNone(data["time_end"])
        self.assertFalse(data["when_ready"])
        order = CrmOrder.objects.get(pk=data["id"])
        self.assertIsNone(order.time_start)
        self.assertIsNone(order.time_end)
        self.assertFalse(order.when_ready)

    def test_create_order_when_ready(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/crm/orders/",
            self._order_payload(time_start="", time_end="", when_ready=True),
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIsNone(data["time_start"])
        self.assertIsNone(data["time_end"])
        self.assertTrue(data["when_ready"])
        order = CrmOrder.objects.get(pk=data["id"])
        self.assertIsNone(order.time_start)
        self.assertIsNone(order.time_end)
        self.assertTrue(order.when_ready)

    def test_create_order_with_multiple_images(self):
        self.client.force_authenticate(user=self.admin)
        payload = self._order_payload(images=[self._jpeg("one.jpg"), self._jpeg("two.jpg")])
        response = self.client.post("/api/crm/orders/", payload, format="multipart")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(len(data["images"]), 2)
        self.assertEqual(data["images"][0]["position"], 0)
        self.assertEqual(data["images"][1]["position"], 1)
        self.assertIn("src", data["images"][0]["image"])
        self.assertIn("srcset", data["images"][0]["image"])

    def test_get_order_detail(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 26),
            time_start=time(12, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/crm/orders/{order.id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], order.id)
        self.assertEqual(data["contact"], "Customer")

    def test_put_order_fields_and_images(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 26),
            time_start=time(12, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        keep = CrmOrderImage.objects.create(order=order, image=self._jpeg("keep.jpg"), position=0)
        drop = CrmOrderImage.objects.create(order=order, image=self._jpeg("drop.jpg"), position=1)

        self.client.force_authenticate(user=self.admin)
        payload = self._order_payload(
            contact="Updated",
            weight="3kg",
            cake_price="150.00",
            time_end="14:00:00",
            delete_image_ids=str(drop.id),
            images=[self._jpeg("new.jpg")],
        )
        response = self.client.put(f"/api/crm/orders/{order.id}/", payload, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["contact"], "Updated")
        self.assertEqual(data["weight"], "3kg")
        self.assertEqual(data["cake_price"], "150.00")
        self.assertEqual(data["time_end"], "14:00:00")
        self.assertEqual(len(data["images"]), 2)
        image_ids = {img["id"] for img in data["images"]}
        self.assertIn(keep.id, image_ids)
        self.assertNotIn(drop.id, image_ids)
        self.assertFalse(CrmOrderImage.objects.filter(pk=drop.id).exists())

    def test_delete_marks_order_deleted(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 26),
            time_start=time(12, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f"/api/crm/orders/{order.id}/")
        self.assertEqual(response.status_code, 204)
        order.refresh_from_db()
        self.assertTrue(order.deleted)
        self.assertTrue(CrmOrder.objects.filter(pk=order.id).exists())

    def test_deleted_orders_excluded_from_date_and_month_lists(self):
        target_date = date(2026, 8, 26)
        live = CrmOrder.objects.create(
            date=target_date,
            time_start=time(10, 0),
            contact="Live",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        CrmOrder.objects.create(
            date=target_date,
            time_start=time(11, 0),
            contact="Deleted",
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            weight="1kg",
            filling="Chocolate",
            cake_price=Decimal("70.00"),
            prepayment=Decimal("0.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
            deleted=True,
        )
        self.client.force_authenticate(user=self.user)

        by_date = self.client.get("/api/crm/orders/", {"date": "2026-08-26"})
        self.assertEqual(by_date.status_code, 200)
        date_ids = [item["id"] for item in by_date.json()["orders"]]
        self.assertEqual(date_ids, [live.id])

        by_month = self.client.get("/api/crm/orders/", {"month": "2026-08"})
        self.assertEqual(by_month.status_code, 200)
        month_ids = [item["id"] for item in by_month.json()["orders"]]
        self.assertEqual(month_ids, [live.id])

    def test_deleted_order_detail_methods_return_404(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 26),
            time_start=time(12, 0),
            contact="Deleted",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
            deleted=True,
        )
        self.client.force_authenticate(user=self.admin)
        detail_url = f"/api/crm/orders/{order.id}/"

        get_response = self.client.get(detail_url)
        self.assertEqual(get_response.status_code, 404)

        put_response = self.client.put(detail_url, self._order_payload(), format="multipart")
        self.assertEqual(put_response.status_code, 404)

        patch_response = self.client.patch(detail_url, {"is_paid": True}, format="json")
        self.assertEqual(patch_response.status_code, 404)

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, 404)
        order.refresh_from_db()
        self.assertTrue(order.deleted)

    def test_create_assigns_client_token(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 26),
            time_start=time(12, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        self.assertRegex(order.client_token, r"^[0-9a-f]{64}$")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/crm/orders/{order.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["client_token"], order.client_token)

    def test_client_order_unauthenticated_ok(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 26),
            time_start=time(12, 0),
            contact="+995555111222",
            nickname="@cake",
            delivery_address="",
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            weight="2kg",
            filling="Vanilla",
            description="No nuts",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        response = self.client.get(f"/api/crm/orders/client/{order.client_token}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], order.id)
        self.assertEqual(data["contact"], "+995555111222")
        self.assertEqual(data["nickname"], "@cake")
        self.assertEqual(data["weight"], "2kg")
        self.assertEqual(data["filling"], "Vanilla")
        self.assertEqual(data["description"], "No nuts")
        self.assertEqual(data["cake_price"], "120.00")
        self.assertEqual(data["prepayment"], "30.00")
        self.assertFalse(data["is_paid"])
        self.assertEqual(data["payment_type"], "cash")
        self.assertIsNone(data["google_maps_url"])
        self.assertNotIn("taken_by_name", data)
        self.assertNotIn("client_token", data)
        self.assertEqual(response["Cache-Control"], "private, no-store, no-cache, must-revalidate")
        self.assertEqual(response["Pragma"], "no-cache")
        self.assertEqual(
            response["X-Robots-Tag"],
            "noindex, nofollow, noarchive, nosnippet, noimageindex",
        )

    def test_client_order_unknown_token_404(self):
        response = self.client.get(
            "/api/crm/orders/client/" + ("a" * 64) + "/"
        )
        self.assertEqual(response.status_code, 404)

    def test_client_order_deleted_404(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 26),
            time_start=time(12, 0),
            contact="Deleted",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
            deleted=True,
        )
        response = self.client.get(f"/api/crm/orders/client/{order.client_token}/")
        self.assertEqual(response.status_code, 404)

    @patch("crm.google_maps.resolve_google_maps_url")
    @patch("crm.yandex_maps.resolve_yandex_maps_url")
    def test_client_order_does_not_resolve_maps_on_get(self, resolve_yandex, resolve_google):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 26),
            time_start=time(12, 0),
            contact="Customer",
            delivery_address="Rustaveli 12, Batumi",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        response = self.client.get(f"/api/crm/orders/client/{order.client_token}/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["google_maps_url"])
        resolve_yandex.assert_not_called()
        resolve_google.assert_not_called()

    def test_client_order_google_maps_url_from_cache(self):
        ResolvedGoogleAddress.objects.create(
            address="Rustaveli 12, Batumi",
            google_url="https://www.google.com/maps/search/?api=1&query=41.623987,41.645449",
        )
        order = CrmOrder.objects.create(
            date=date(2026, 8, 26),
            time_start=time(12, 0),
            contact="Customer",
            delivery_address="Rustaveli 12, Batumi",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        response = self.client.get(f"/api/crm/orders/client/{order.client_token}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["google_maps_url"],
            "https://www.google.com/maps/search/?api=1&query=41.623987,41.645449",
        )

    @patch("crm.views.resolve_google_maps_url")
    @patch("crm.views.resolve_yandex_maps_url")
    def test_client_order_map(self, resolve_yandex, resolve_google):
        resolve_yandex.return_value = "https://yandex.com/maps/?text=Rustaveli"
        resolve_google.return_value = (
            "https://www.google.com/maps/search/?api=1&query=41.623987,41.645449"
        )
        order = CrmOrder.objects.create(
            date=date(2026, 8, 26),
            time_start=time(12, 0),
            contact="Customer",
            delivery_address="Rustaveli 12, Batumi",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        response = self.client.get(f"/api/crm/orders/client/{order.client_token}/map/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["url"],
            "https://www.google.com/maps/search/?api=1&query=41.623987,41.645449",
        )
        self.assertEqual(response["Cache-Control"], "private, no-store, no-cache, must-revalidate")
        resolve_yandex.assert_called_once_with("Rustaveli 12, Batumi")
        resolve_google.assert_called_once_with(
            "Rustaveli 12, Batumi",
            "https://yandex.com/maps/?text=Rustaveli",
        )

    def test_client_order_map_unknown_token_404(self):
        response = self.client.get("/api/crm/orders/client/" + ("a" * 64) + "/map/")
        self.assertEqual(response.status_code, 404)

    def test_client_order_map_no_address_404(self):
        order = CrmOrder.objects.create(
            date=date(2026, 8, 26),
            time_start=time(12, 0),
            contact="Customer",
            delivery_address="",
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
        )
        response = self.client.get(f"/api/crm/orders/client/{order.client_token}/map/")
        self.assertEqual(response.status_code, 404)
