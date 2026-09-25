from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from crm.flowwow import _upsert_crm_order
from crm.models import CrmOrder, CrmOrderEvent
from crm.tests.test_flowwow_orders import _flowwow_order, _image_response
from crm.website import create_crm_order_from_website_order, mark_crm_order_paid_for_website_order
from orders.models import DeliveryAddress, Order, OrderItem

_TB = ZoneInfo("Asia/Tbilisi")


class CrmOrderHistoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="worker", password="password")
        self.admin = User.objects.create_user(username="admin", password="password", is_staff=True)

    def _order_payload(self):
        return {
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
            "internal_description": "Kitchen only",
            "cake_price": "120.00",
            "prepayment": "30.00",
            "is_paid": False,
            "payment_type": CrmOrder.PAYMENT_CASH,
        }

    def _order(self, **overrides):
        fields = {
            "date": date(2026, 8, 26),
            "time_start": time(12, 0),
            "contact": "Customer",
            "fulfillment_type": CrmOrder.FULFILLMENT_DELIVERY,
            "weight": "2kg",
            "filling": "Vanilla",
            "cake_price": Decimal("120.00"),
            "prepayment": Decimal("30.00"),
            "is_paid": False,
            "payment_type": CrmOrder.PAYMENT_CASH,
            "status": CrmOrder.STATUS_NEW,
        }
        fields.update(overrides)
        return CrmOrder.objects.create(**fields)

    def test_staff_create_records_actor(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post("/api/crm/orders/", self._order_payload(), format="multipart")
        self.assertEqual(response.status_code, 201)
        event = CrmOrderEvent.objects.get(order_id=response.json()["id"])
        self.assertEqual(event.action, CrmOrderEvent.ACTION_CREATED)
        self.assertEqual(event.source, CrmOrderEvent.SOURCE_CRM)
        self.assertEqual(event.actor, self.admin)
        self.assertIsNone(event.changes["contact"]["old"])
        self.assertEqual(event.changes["contact"]["new"], "Customer")
        self.assertEqual(event.changes["status"]["new"], CrmOrder.STATUS_NEW)

    def test_status_patch_records_diff(self):
        order = self._order()
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_IN_WORK},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        event = CrmOrderEvent.objects.get(order=order)
        self.assertEqual(event.action, CrmOrderEvent.ACTION_UPDATED)
        self.assertEqual(event.source, CrmOrderEvent.SOURCE_CRM)
        self.assertEqual(event.actor, self.user)
        self.assertEqual(
            event.changes["status"],
            {"old": CrmOrder.STATUS_NEW, "new": CrmOrder.STATUS_IN_WORK},
        )
        self.assertEqual(event.changes["taken_by_id"], {"old": None, "new": self.user.id})

    def test_soft_delete_records_deleted(self):
        order = self._order()
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f"/api/crm/orders/{order.id}/")
        self.assertEqual(response.status_code, 204)
        event = CrmOrderEvent.objects.get(order=order)
        self.assertEqual(event.action, CrmOrderEvent.ACTION_DELETED)
        self.assertEqual(event.source, CrmOrderEvent.SOURCE_CRM)
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(event.changes, {"deleted": {"old": False, "new": True}})

    def test_website_create_and_payment(self):
        website_order = Order.objects.create(
            fulfillment_type=Order.FULFILLMENT_DELIVERY,
            payment_method=Order.PAYMENT_CARD,
            customer_name="Anna",
            customer_phone="+995555111222",
            timeslot_start=datetime(2026, 5, 21, 16, 0, tzinfo=_TB),
            timeslot_end=datetime(2026, 5, 21, 17, 0, tzinfo=_TB),
            total=Decimal("100.00"),
        )
        DeliveryAddress.objects.create(order=website_order, street="Rustaveli", city="Batumi")
        OrderItem.objects.create(
            order=website_order,
            product_name="Cake",
            unit_price=Decimal("100.00"),
            quantity=1,
            line_total=Decimal("100.00"),
        )
        crm_order = create_crm_order_from_website_order(website_order)
        created = CrmOrderEvent.objects.get(order=crm_order)
        self.assertEqual(created.action, CrmOrderEvent.ACTION_CREATED)
        self.assertEqual(created.source, CrmOrderEvent.SOURCE_WEBSITE)
        self.assertIsNone(created.actor_id)
        self.assertEqual(created.changes["status"]["new"], CrmOrder.STATUS_UNCONFIRMED)

        mark_crm_order_paid_for_website_order(website_order)
        paid = CrmOrderEvent.objects.exclude(pk=created.pk).get(order=crm_order)
        self.assertEqual(paid.action, CrmOrderEvent.ACTION_UPDATED)
        self.assertEqual(paid.source, CrmOrderEvent.SOURCE_WEBSITE)
        self.assertIsNone(paid.actor_id)
        self.assertEqual(paid.changes["is_paid"], {"old": False, "new": True})
        self.assertNotIn("status", paid.changes)
        self.assertEqual(paid.changes["prepayment"], {"old": "0.00", "new": "100.00"})

    @patch("crm.flowwow.requests.get")
    def test_flowwow_resync_without_changes_skips_event(self, mock_get):
        mock_get.return_value = _image_response()
        _upsert_crm_order(_flowwow_order())
        created = CrmOrderEvent.objects.get()
        self.assertEqual(created.action, CrmOrderEvent.ACTION_CREATED)
        self.assertEqual(created.source, CrmOrderEvent.SOURCE_FLOWWOW)
        self.assertIsNone(created.actor_id)
        _upsert_crm_order(_flowwow_order())
        self.assertEqual(CrmOrderEvent.objects.count(), 1)

    def test_events_api_hides_internal_description_from_non_staff(self):
        self.client.force_authenticate(user=self.admin)
        created = self.client.post("/api/crm/orders/", self._order_payload(), format="multipart")
        self.assertEqual(created.status_code, 201)
        order_id = created.json()["id"]
        self.client.force_authenticate(user=self.user)
        patched = self.client.patch(
            f"/api/crm/orders/{order_id}/",
            {"status": CrmOrder.STATUS_IN_WORK},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)

        worker_response = self.client.get(f"/api/crm/orders/{order_id}/events/")
        self.assertEqual(worker_response.status_code, 200)
        worker_events = worker_response.json()
        self.assertEqual(
            [event["action"] for event in worker_events],
            [CrmOrderEvent.ACTION_UPDATED, CrmOrderEvent.ACTION_CREATED],
        )
        self.assertEqual(worker_events[0]["actor_name"], "worker")
        self.assertEqual(worker_events[0]["source"], CrmOrderEvent.SOURCE_CRM)
        self.assertEqual(worker_events[0]["changes"]["taken_by_id"]["new"]["name"], "worker")
        created_event = worker_events[1]
        self.assertIsNone(created_event["actor_telegram_url"])
        self.assertEqual(created_event["actor_name"], "admin")
        self.assertNotIn("internal_description", created_event["changes"])

        self.client.force_authenticate(user=self.admin)
        admin_response = self.client.get(f"/api/crm/orders/{order_id}/events/")
        self.assertEqual(admin_response.status_code, 200)
        admin_created = next(
            event for event in admin_response.json() if event["action"] == CrmOrderEvent.ACTION_CREATED
        )
        self.assertEqual(admin_created["changes"]["internal_description"]["new"], "Kitchen only")
