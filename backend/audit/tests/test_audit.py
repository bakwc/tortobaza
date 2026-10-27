from contextlib import contextmanager
from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from audit.context import bind, release
from audit.models import AuditEvent
from crm.history import record_crm_order_event
from crm.models import CrmOrder, CrmOrderEvent
from inventory.models import Supply, SupplyLine
from menu.models import UNIT_GRAM, Ingredient


@contextmanager
def actor(user):
    tokens = bind(user)
    try:
        yield
    finally:
        release(tokens)


class AuditLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="worker", password="password")
        self.staff = User.objects.create_user(username="staff", password="password")
        self.finance = User.objects.create_user(username="finance", password="password")
        UserProfile.objects.create(user=self.finance, is_finance_admin=True)

    def test_update_records_raw_field_diff_and_skips_anonymous(self):
        ingredient = Ingredient.objects.create(name="Flour", unit=UNIT_GRAM)
        ingredient.name = "Wheat"
        ingredient.save()
        self.assertFalse(AuditEvent.objects.filter(model="ingredient").exists())
        with actor(self.user):
            with self.captureOnCommitCallbacks(execute=True):
                ingredient.sale_price = Decimal("2.00")
                ingredient.save()
        event = AuditEvent.objects.get(model="ingredient")
        self.assertEqual(event.action, AuditEvent.ACTION_UPDATED)
        self.assertEqual(event.actor, self.user)
        self.assertEqual(event.changes["sale_price"], {"old": None, "new": "2.00"})
        self.assertNotIn("name", event.changes)

    def test_delete_records_old_values(self):
        ingredient = Ingredient.objects.create(name="Flour", unit=UNIT_GRAM, sale_price=Decimal("1.50"))
        with actor(self.user):
            with self.captureOnCommitCallbacks(execute=True):
                ingredient.delete()
        event = AuditEvent.objects.get(model="ingredient")
        self.assertEqual(event.action, AuditEvent.ACTION_DELETED)
        self.assertEqual(event.changes["name"], {"old": "Flour", "new": None})
        self.assertEqual(event.changes["sale_price"], {"old": "1.50", "new": None})
        self.assertFalse(Ingredient.objects.filter(name="Flour").exists())

    def test_rolled_back_delete_is_not_recorded(self):
        ingredient = Ingredient.objects.create(name="Sugar", unit=UNIT_GRAM)
        with actor(self.user):
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError):
                    with transaction.atomic():
                        ingredient.delete()
                        raise RuntimeError("rollback")
        self.assertFalse(AuditEvent.objects.filter(model="ingredient").exists())

    def test_supply_line_rewrite_and_quantity_change(self):
        ingredient = Ingredient.objects.create(name="Flour", unit=UNIT_GRAM)
        supply = Supply.objects.create(date=date(2026, 10, 1))
        SupplyLine.objects.create(
            supply=supply,
            ingredient=ingredient,
            quantity=Decimal("1.000"),
            total=Decimal("5.00"),
        )
        with actor(self.user):
            with self.captureOnCommitCallbacks(execute=True):
                with transaction.atomic():
                    supply.save()
                    supply.lines.all().delete()
                    SupplyLine.objects.create(
                        supply=supply,
                        ingredient=ingredient,
                        quantity=Decimal("1.000"),
                        total=Decimal("5.00"),
                    )
        self.assertFalse(AuditEvent.objects.filter(model="supply").exists())
        with actor(self.user):
            with self.captureOnCommitCallbacks(execute=True):
                with transaction.atomic():
                    supply.save()
                    supply.lines.all().delete()
                    SupplyLine.objects.create(
                        supply=supply,
                        ingredient=ingredient,
                        quantity=Decimal("2.000"),
                        total=Decimal("5.00"),
                    )
        event = AuditEvent.objects.get(model="supply")
        self.assertEqual(event.action, AuditEvent.ACTION_UPDATED)
        self.assertEqual(event.changes["lines"]["old"][0]["ingredient_id"], ingredient.pk)
        self.assertEqual(event.changes["lines"]["old"][0]["quantity"], "1.000")
        self.assertEqual(event.changes["lines"]["new"][0]["quantity"], "2.000")

    def test_password_is_not_stored(self):
        self.user.set_password("another-password")
        self.user.username = "renamed"
        with actor(self.finance):
            with self.captureOnCommitCallbacks(execute=True):
                self.user.save()
        event = AuditEvent.objects.get(model="user")
        self.assertNotIn("password", event.changes)
        self.assertEqual(event.changes["username"], {"old": "worker", "new": "renamed"})

    def test_crm_order_event_is_mirrored(self):
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
            status=CrmOrder.STATUS_NEW,
        )
        event = record_crm_order_event(
            order,
            CrmOrderEvent.ACTION_CREATED,
            CrmOrderEvent.SOURCE_WEBSITE,
            None,
            None,
        )
        audit = AuditEvent.objects.get(model="crmorder")
        self.assertEqual(audit.action, AuditEvent.ACTION_CREATED)
        self.assertIsNone(audit.actor_id)
        self.assertEqual(audit.source, AuditEvent.SOURCE_WEBSITE)
        self.assertEqual(audit.object_id, str(order.pk))
        self.assertEqual(audit.changes, event.changes)
        self.assertEqual(audit.changes["contact"], {"old": None, "new": "Customer"})

    def test_list_is_finance_admin_only(self):
        AuditEvent.objects.create(
            actor=self.finance,
            action=AuditEvent.ACTION_CREATED,
            app_label="menu",
            model="ingredient",
            object_id="1",
            object_label="Flour",
            database="default",
            source=AuditEvent.SOURCE_USER,
            changes={"name": {"old": None, "new": "Flour"}},
        )
        client = APIClient()
        client.force_authenticate(user=self.staff)
        denied = client.get("/api/audit/events/")
        self.assertEqual(denied.status_code, 403)
        client.force_authenticate(user=self.finance)
        response = client.get("/api/audit/events/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["results"][0]["object_label"], "Flour")
        self.assertEqual(body["results"][0]["changes"]["name"], {"old": None, "new": "Flour"})
        self.assertEqual(body["results"][0]["actor_name"], "finance")
