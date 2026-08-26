import io
from datetime import date, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from crm.models import CrmOrder, CrmOrderImage

_TB = ZoneInfo("Asia/Tbilisi")


class CrmOrdersApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="staff", password="password")

    def test_unauthenticated_access_denied(self):
        response = self.client.get("/api/crm/orders/")
        self.assertEqual(response.status_code, 403)

        patch_response = self.client.patch("/api/crm/orders/1/", {"is_delivered": True})
        self.assertEqual(patch_response.status_code, 403)

        post_response = self.client.post("/api/crm/orders/", {})
        self.assertEqual(post_response.status_code, 403)

        get_detail = self.client.get("/api/crm/orders/1/")
        self.assertEqual(get_detail.status_code, 403)

        put_response = self.client.put("/api/crm/orders/1/", {})
        self.assertEqual(put_response.status_code, 403)

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
            is_delivered=False,
            is_paid=False,
            payment_type=CrmOrder.PAYMENT_CASH,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"is_delivered": True, "is_paid": True, "weight": "99kg"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()
        self.assertTrue(order.is_delivered)
        self.assertTrue(order.is_paid)
        self.assertEqual(order.weight, "2kg")

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
            "is_delivered": False,
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

    def test_create_order(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/crm/orders/", self._order_payload(), format="multipart")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["contact"], "Customer")
        self.assertEqual(data["date"], "2026-08-26")
        self.assertEqual(data["time_start"], "12:00:00")
        self.assertEqual(data["nickname"], "@nick")
        self.assertEqual(len(data["images"]), 0)
        self.assertTrue(CrmOrder.objects.filter(pk=data["id"]).exists())

    def test_create_order_with_multiple_images(self):
        self.client.force_authenticate(user=self.user)
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

        self.client.force_authenticate(user=self.user)
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
