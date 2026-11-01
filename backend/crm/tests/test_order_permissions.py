from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.permissions import grant
from crm.models import CrmOrder


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

    def test_viewer_reads_and_changes_status(self):
        self.client.force_authenticate(user=self.viewer)
        read = self.client.get(f"/api/crm/orders/{self.order.id}/")
        self.assertEqual(read.status_code, 200)
        patched = self.client.patch(
            f"/api/crm/orders/{self.order.id}/",
            {"status": CrmOrder.STATUS_IN_WORK},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
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
