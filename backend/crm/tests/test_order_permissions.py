from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.permissions import grant
from audit.models import AuditEvent
from crm.models import CrmOrder, CrmOrderEvent, ResolvedGoogleAddress


class OrderSectionPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(username="viewer", password="password")
        self.editor = User.objects.create_user(username="editor", password="password")
        grant(self.viewer, "view_orders")
        grant(self.editor, "edit_orders")
        self.order = CrmOrder.objects.create(
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
            status=CrmOrder.STATUS_NEW,
        )

    def test_viewer_reads_but_cannot_change_status(self):
        self.client.force_authenticate(user=self.viewer)
        read = self.client.get(f"/api/crm/orders/{self.order.id}/")
        self.assertEqual(read.status_code, 200)
        same = self.client.patch(
            f"/api/crm/orders/{self.order.id}/",
            {"status": CrmOrder.STATUS_NEW},
            format="json",
        )
        self.assertEqual(same.status_code, 200)
        patched = self.client.patch(
            f"/api/crm/orders/{self.order.id}/",
            {"status": CrmOrder.STATUS_IN_WORK},
            format="json",
        )
        self.assertEqual(patched.status_code, 403)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, CrmOrder.STATUS_NEW)

    def test_pickup_delivered_permission_does_not_deliver_delivery(self):
        grant(self.viewer, "set_order_pickup_status_delivered")
        self.viewer = User.objects.get(pk=self.viewer.pk)
        pickup = CrmOrder.objects.create(
            date=date(2026, 8, 26),
            time_start=time(12, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            weight="2kg",
            filling="Vanilla",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("30.00"),
            is_paid=False,
            payment_type=CrmOrder.PAYMENT_CASH,
            status=CrmOrder.STATUS_READY,
        )
        self.client.force_authenticate(user=self.viewer)
        denied = self.client.patch(
            f"/api/crm/orders/{self.order.id}/",
            {"status": CrmOrder.STATUS_DELIVERED},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        allowed = self.client.patch(
            f"/api/crm/orders/{pickup.id}/",
            {"status": CrmOrder.STATUS_DELIVERED},
            format="json",
        )
        self.assertEqual(allowed.status_code, 200)
        self.order.refresh_from_db()
        pickup.refresh_from_db()
        self.assertEqual(self.order.status, CrmOrder.STATUS_NEW)
        self.assertEqual(pickup.status, CrmOrder.STATUS_DELIVERED)

    def test_editor_changes_status_without_status_permissions(self):
        self.client.force_authenticate(user=self.editor)
        patched = self.client.patch(
            f"/api/crm/orders/{self.order.id}/",
            {"status": CrmOrder.STATUS_IN_WORK},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, CrmOrder.STATUS_IN_WORK)

    def test_take_in_work_requires_in_work_permission(self):
        self.client.force_authenticate(user=self.viewer)
        denied = self.client.patch(
            f"/api/crm/orders/{self.order.id}/",
            {"take_in_work": True},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, CrmOrder.STATUS_NEW)
        grant(self.viewer, "set_order_delivery_status_in_work")
        self.viewer = User.objects.get(pk=self.viewer.pk)
        self.client.force_authenticate(user=self.viewer)
        allowed = self.client.patch(
            f"/api/crm/orders/{self.order.id}/",
            {"take_in_work": True},
            format="json",
        )
        self.assertEqual(allowed.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, CrmOrder.STATUS_IN_WORK)

    def test_viewer_cannot_edit_or_delete(self):
        self.client.force_authenticate(user=self.viewer)
        paid = self.client.patch(
            f"/api/crm/orders/{self.order.id}/",
            {"is_paid": True},
            format="json",
        )
        self.assertEqual(paid.status_code, 403)
        deleted = self.client.delete(f"/api/crm/orders/{self.order.id}/")
        self.assertEqual(deleted.status_code, 403)
        self.order.refresh_from_db()
        self.assertFalse(self.order.deleted)
        self.assertFalse(self.order.is_paid)

    def test_editor_deletes_order(self):
        self.client.force_authenticate(user=self.editor)
        deleted = self.client.delete(f"/api/crm/orders/{self.order.id}/")
        self.assertEqual(deleted.status_code, 204)
        self.order.refresh_from_db()
        self.assertTrue(self.order.deleted)


_GOOGLE_URL = "https://www.google.com/maps/search/?api=1&query=41.623987,41.645449"
_ADDRESS = "Rustaveli 12, Batumi"


def _party_order(fulfillment_type: str) -> CrmOrder:
    return CrmOrder.objects.create(
        date=date(2026, 8, 26),
        time_start=time(12, 0),
        contact="Recipient +995555111222",
        nickname="Sender",
        delivery_address=_ADDRESS,
        fulfillment_type=fulfillment_type,
        weight="2kg",
        filling="Vanilla",
        cake_price=Decimal("120.00"),
        prepayment=Decimal("30.00"),
        is_paid=False,
        payment_type=CrmOrder.PAYMENT_CASH,
        status=CrmOrder.STATUS_NEW,
    )


def _party_rows(client: APIClient) -> dict[int, dict]:
    response = client.get("/api/crm/orders/", {"date": "2026-08-26"})
    assert response.status_code == 200
    return {row["id"]: row for row in response.json()["orders"]}


class OrderPartyPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(username="viewer", password="password")
        self.delivery = User.objects.create_user(username="delivery", password="password")
        self.pickup = User.objects.create_user(username="pickup", password="password")
        self.editor = User.objects.create_user(username="editor", password="password")
        self.historian = User.objects.create_user(username="historian", password="password")
        grant(self.viewer, "view_orders")
        grant(
            self.delivery,
            "view_orders",
            "view_order_delivery_address",
            "view_order_delivery_contacts",
        )
        grant(
            self.pickup,
            "view_orders",
            "view_order_pickup_address",
            "view_order_pickup_contacts",
        )
        grant(self.editor, "edit_orders")
        grant(self.historian, "view_history")
        ResolvedGoogleAddress.objects.create(address=_ADDRESS, google_url=_GOOGLE_URL)
        self.delivery_order = _party_order(CrmOrder.FULFILLMENT_DELIVERY)
        self.pickup_order = _party_order(CrmOrder.FULFILLMENT_PICKUP)
        self.changes = {
            "contact": {"old": "Old", "new": "Recipient +995555111222"},
            "nickname": {"old": "", "new": "Sender"},
            "phones": {"old": [], "new": ["995555111222"]},
            "delivery_address": {"old": "", "new": _ADDRESS},
            "cake_price": {"old": "0.00", "new": "120.00"},
            "delivery_price": {"old": "0.00", "new": "0.00"},
            "prepayment": {"old": "0.00", "new": "30.00"},
            "payment_type": {"old": "unknown", "new": "cash"},
            "status": {"old": CrmOrder.STATUS_NEW, "new": CrmOrder.STATUS_IN_WORK},
        }
        CrmOrderEvent.objects.create(
            order=self.delivery_order,
            action=CrmOrderEvent.ACTION_UPDATED,
            source=CrmOrderEvent.SOURCE_CRM,
            changes=self.changes,
        )
        CrmOrderEvent.objects.create(
            order=self.pickup_order,
            action=CrmOrderEvent.ACTION_UPDATED,
            source=CrmOrderEvent.SOURCE_CRM,
            changes=self.changes,
        )

    def test_viewer_without_party_permissions_gets_blank_fields(self):
        self.client.force_authenticate(user=self.viewer)
        rows = _party_rows(self.client)
        for order in (self.delivery_order, self.pickup_order):
            row = rows[order.id]
            self.assertEqual(row["contact"], "")
            self.assertEqual(row["nickname"], "")
            self.assertEqual(row["phones"], [])
            self.assertEqual(row["delivery_address"], "")
            self.assertIsNone(row["cake_price"])
            self.assertIsNone(row["delivery_price"])
            self.assertIsNone(row["prepayment"])
            self.assertIsNone(row["payment_type"])
            self.assertEqual(row["fulfillment_type"], order.fulfillment_type)
        mapped = self.client.get("/api/crm/orders/map/", {"date": "2026-08-26"})
        self.assertEqual(mapped.status_code, 200)
        self.assertEqual(mapped.json()["orders"], [])

    def test_delivery_permissions_hide_pickup(self):
        self.client.force_authenticate(user=self.delivery)
        rows = _party_rows(self.client)
        delivery = rows[self.delivery_order.id]
        pickup = rows[self.pickup_order.id]
        self.assertEqual(delivery["contact"], "Recipient +995555111222")
        self.assertEqual(delivery["nickname"], "Sender")
        self.assertEqual(delivery["delivery_address"], _ADDRESS)
        self.assertNotEqual(delivery["phones"], [])
        self.assertIsNone(delivery["cake_price"])
        self.assertIsNone(delivery["delivery_price"])
        self.assertIsNone(delivery["prepayment"])
        self.assertEqual(pickup["contact"], "")
        self.assertEqual(pickup["nickname"], "")
        self.assertEqual(pickup["phones"], [])
        self.assertEqual(pickup["delivery_address"], "")
        self.assertIsNone(pickup["cake_price"])
        mapped = self.client.get("/api/crm/orders/map/", {"date": "2026-08-26"})
        self.assertEqual(mapped.status_code, 200)
        self.assertEqual(
            [order["id"] for order in mapped.json()["orders"]],
            [self.delivery_order.id],
        )

    def test_pickup_permissions_hide_delivery(self):
        self.client.force_authenticate(user=self.pickup)
        rows = _party_rows(self.client)
        delivery = rows[self.delivery_order.id]
        pickup = rows[self.pickup_order.id]
        self.assertEqual(delivery["contact"], "")
        self.assertEqual(delivery["delivery_address"], "")
        self.assertEqual(pickup["contact"], "Recipient +995555111222")
        self.assertEqual(pickup["nickname"], "Sender")
        self.assertEqual(pickup["delivery_address"], _ADDRESS)
        self.assertNotEqual(pickup["phones"], [])
        self.assertIsNone(delivery["cake_price"])
        self.assertIsNone(pickup["cake_price"])
        self.assertIsNone(pickup["prepayment"])
        mapped = self.client.get("/api/crm/orders/map/", {"date": "2026-08-26"})
        self.assertEqual(mapped.status_code, 200)
        self.assertEqual(
            [order["id"] for order in mapped.json()["orders"]],
            [self.pickup_order.id],
        )

    def test_editor_sees_both_without_party_permissions(self):
        self.client.force_authenticate(user=self.editor)
        rows = _party_rows(self.client)
        for order in (self.delivery_order, self.pickup_order):
            row = rows[order.id]
            self.assertEqual(row["contact"], "Recipient +995555111222")
            self.assertEqual(row["nickname"], "Sender")
            self.assertEqual(row["delivery_address"], _ADDRESS)
            self.assertNotEqual(row["phones"], [])
            self.assertEqual(row["cake_price"], "120.00")
            self.assertEqual(row["delivery_price"], "0.00")
            self.assertEqual(row["prepayment"], "30.00")
            self.assertEqual(row["payment_type"], "cash")
        mapped = self.client.get("/api/crm/orders/map/", {"date": "2026-08-26"})
        self.assertEqual(mapped.status_code, 200)
        self.assertEqual(
            {order["id"] for order in mapped.json()["orders"]},
            {self.delivery_order.id, self.pickup_order.id},
        )

    def test_price_permission_follows_party(self):
        grant(self.delivery, "view_order_delivery_price")
        grant(self.pickup, "view_order_pickup_price")
        self.delivery = User.objects.get(pk=self.delivery.pk)
        self.pickup = User.objects.get(pk=self.pickup.pk)
        self.client.force_authenticate(user=self.delivery)
        rows = _party_rows(self.client)
        self.assertEqual(rows[self.delivery_order.id]["cake_price"], "120.00")
        self.assertEqual(rows[self.delivery_order.id]["delivery_price"], "0.00")
        self.assertEqual(rows[self.delivery_order.id]["prepayment"], "30.00")
        self.assertEqual(rows[self.delivery_order.id]["payment_type"], "cash")
        self.assertIsNone(rows[self.pickup_order.id]["cake_price"])
        self.assertIsNone(rows[self.pickup_order.id]["prepayment"])
        self.assertIsNone(rows[self.pickup_order.id]["payment_type"])
        shown = self.client.get(f"/api/crm/orders/{self.delivery_order.id}/events/")
        self.assertEqual(shown.json()[0]["changes"]["cake_price"]["new"], "120.00")
        hidden = self.client.get(f"/api/crm/orders/{self.pickup_order.id}/events/")
        self.assertNotIn("cake_price", hidden.json()[0]["changes"])
        self.assertNotIn("prepayment", hidden.json()[0]["changes"])

        self.client.force_authenticate(user=self.pickup)
        pickup_rows = _party_rows(self.client)
        self.assertIsNone(pickup_rows[self.delivery_order.id]["cake_price"])
        self.assertEqual(pickup_rows[self.pickup_order.id]["cake_price"], "120.00")
        history = self.client.get(f"/api/crm/orders/{self.pickup_order.id}/client-orders/")
        self.assertEqual(history.status_code, 200)
        history_rows = {row["id"]: row for row in history.json()["orders"]}
        self.assertEqual(history_rows[self.pickup_order.id]["total"], "120.00")
        self.assertIsNone(history_rows[self.delivery_order.id]["total"])

    def test_order_events_redact_by_party(self):
        self.client.force_authenticate(user=self.viewer)
        hidden = self.client.get(f"/api/crm/orders/{self.delivery_order.id}/events/")
        self.assertEqual(hidden.status_code, 200)
        hidden_changes = hidden.json()[0]["changes"]
        self.assertNotIn("contact", hidden_changes)
        self.assertNotIn("nickname", hidden_changes)
        self.assertNotIn("phones", hidden_changes)
        self.assertNotIn("delivery_address", hidden_changes)
        self.assertNotIn("cake_price", hidden_changes)
        self.assertNotIn("delivery_price", hidden_changes)
        self.assertNotIn("prepayment", hidden_changes)
        self.assertNotIn("payment_type", hidden_changes)
        self.assertEqual(hidden_changes["status"]["new"], CrmOrder.STATUS_IN_WORK)

        self.client.force_authenticate(user=self.delivery)
        shown = self.client.get(f"/api/crm/orders/{self.delivery_order.id}/events/")
        self.assertEqual(shown.json()[0]["changes"]["contact"]["new"], "Recipient +995555111222")
        self.assertEqual(shown.json()[0]["changes"]["delivery_address"]["new"], _ADDRESS)
        self.assertNotIn("cake_price", shown.json()[0]["changes"])
        pickup = self.client.get(f"/api/crm/orders/{self.pickup_order.id}/events/")
        self.assertNotIn("contact", pickup.json()[0]["changes"])
        self.assertNotIn("delivery_address", pickup.json()[0]["changes"])
        self.assertNotIn("cake_price", pickup.json()[0]["changes"])

    def test_audit_redacts_crm_order_contact_and_address(self):
        AuditEvent.objects.create(
            action=AuditEvent.ACTION_UPDATED,
            app_label="crm",
            model="crmorder",
            object_id=str(self.delivery_order.id),
            object_label=f"{self.delivery_order.date} Recipient +995555111222",
            database="default",
            source=AuditEvent.SOURCE_CRM,
            changes=self.changes,
        )
        missing = AuditEvent.objects.create(
            action=AuditEvent.ACTION_UPDATED,
            app_label="crm",
            model="crmorder",
            object_id="999999",
            object_label="2026-08-26 Missing",
            database="default",
            source=AuditEvent.SOURCE_CRM,
            changes=self.changes,
        )
        self.client.force_authenticate(user=self.historian)
        response = self.client.get("/api/audit/events/")
        self.assertEqual(response.status_code, 200)
        rows = {row["object_id"]: row for row in response.json()["results"]}
        delivery = rows[str(self.delivery_order.id)]
        self.assertEqual(delivery["object_label"], f"{self.delivery_order.date} #{self.delivery_order.id}")
        self.assertNotIn("contact", delivery["changes"])
        self.assertNotIn("nickname", delivery["changes"])
        self.assertNotIn("phones", delivery["changes"])
        self.assertNotIn("delivery_address", delivery["changes"])
        self.assertNotIn("cake_price", delivery["changes"])
        self.assertNotIn("prepayment", delivery["changes"])
        self.assertEqual(delivery["changes"]["status"]["new"], CrmOrder.STATUS_IN_WORK)
        self.assertEqual(rows[missing.object_id]["object_label"], "#999999")
        self.assertNotIn("contact", rows[missing.object_id]["changes"])

        grant(self.historian, "edit_orders")
        self.historian = User.objects.get(pk=self.historian.pk)
        self.client.force_authenticate(user=self.historian)
        kept = self.client.get("/api/audit/events/", {"object_id": str(self.delivery_order.id)})
        self.assertEqual(kept.status_code, 200)
        row = kept.json()["results"][0]
        self.assertEqual(row["object_label"], f"{self.delivery_order.date} Recipient +995555111222")
        self.assertEqual(row["changes"]["contact"]["new"], "Recipient +995555111222")
        self.assertEqual(row["changes"]["delivery_address"]["new"], _ADDRESS)
        self.assertEqual(row["changes"]["cake_price"]["new"], "120.00")
        self.assertEqual(row["changes"]["payment_type"]["new"], "cash")
