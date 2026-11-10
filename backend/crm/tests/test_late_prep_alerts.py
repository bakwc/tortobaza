from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from accounts.models import UserProfile
from crm.late_prep_alerts import notify_late_preps, refresh_order_late_prep
from crm.models import CrmOrder
from crm.telegram import crm_order_prep_datetime

_TB = ZoneInfo("Asia/Tbilisi")


def _order(**kwargs) -> CrmOrder:
    fields = {
        "date": date(2026, 10, 24),
        "time_start": time(19, 0),
        "contact": "Customer",
        "delivery_address": "Rustaveli 1",
        "fulfillment_type": CrmOrder.FULFILLMENT_DELIVERY,
        "weight": "2kg",
        "filling": "Vanilla",
        "cake_price": Decimal("120.00"),
        "status": CrmOrder.STATUS_NEW,
    }
    fields.update(kwargs)
    return CrmOrder.objects.create(**fields)


@override_settings(TELEGRAM_BOT_TOKEN="bot-token", TELEGRAM_CRM_CHAT_ID="crm-chat")
class LatePrepAlertTests(TestCase):
    def setUp(self):
        self.calls = []

        def fake(method, payload):
            self.calls.append((method, payload))
            if method == "sendMessage":
                return {"ok": True, "result": {"message_id": 501}}
            return {"ok": True, "result": True}

        self.patcher = patch("crm.late_prep_alerts._telegram_json", side_effect=fake)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_first_send_then_edit_minutes(self):
        order = _order(fulfillment_type=CrmOrder.FULFILLMENT_PICKUP)
        prep = crm_order_prep_datetime(order)
        refresh_order_late_prep(order.pk, prep)
        refresh_order_late_prep(order.pk, prep + timedelta(minutes=15))
        self.assertEqual([call[0] for call in self.calls], ["sendMessage", "editMessageText"])
        self.assertEqual(self.calls[0][1]["chat_id"], "crm-chat")
        self.assertEqual(
            self.calls[0][1]["text"],
            f"Опоздание по заказу #{order.pk} на 1 минуту - должен был быть приготовлен к 18:30, никто не готовит",
        )
        self.assertEqual(self.calls[1][1]["message_id"], 501)
        self.assertEqual(
            self.calls[1][1]["text"],
            f"Опоздание по заказу #{order.pk} на 15 минут - должен был быть приготовлен к 18:30, никто не готовит",
        )
        order.refresh_from_db()
        self.assertEqual(order.late_prep_message_id, 501)
        self.assertFalse(order.late_prep_closed)

    def test_cook_name(self):
        user = User.objects.create_user(username="vasya", password="password")
        UserProfile.objects.create(user=user, internal_name="Вася Пупкин")
        order = _order(taken_by=user)
        prep = crm_order_prep_datetime(order)
        refresh_order_late_prep(order.pk, prep + timedelta(minutes=15))
        self.assertEqual(
            self.calls[0][1]["text"],
            f"Опоздание по заказу #{order.pk} на 15 минут - должен был быть приготовлен к 18:30, готовит Вася Пупкин",
        )

    def test_skip_late_alerts_does_not_send(self):
        user = User.objects.create_user(username="vasya", password="password")
        UserProfile.objects.create(user=user, internal_name="Вася Пупкин", skip_late_alerts=True)
        order = _order(taken_by=user)
        prep = crm_order_prep_datetime(order)
        refresh_order_late_prep(order.pk, prep + timedelta(minutes=15))
        self.assertEqual(self.calls, [])
        order.refresh_from_db()
        self.assertIsNone(order.late_prep_message_id)

    def test_ready_edits_once_then_stops(self):
        order = _order()
        prep = crm_order_prep_datetime(order)
        refresh_order_late_prep(order.pk, prep + timedelta(minutes=15))
        order.status = CrmOrder.STATUS_READY
        order.save(update_fields=["status", "updated_at"])
        refresh_order_late_prep(order.pk, prep + timedelta(minutes=20))
        refresh_order_late_prep(order.pk, prep + timedelta(minutes=40))
        self.assertEqual([call[0] for call in self.calls], ["sendMessage", "editMessageText"])
        self.assertIn("на 20 минут", self.calls[1][1]["text"])
        order.refresh_from_db()
        self.assertTrue(order.late_prep_closed)

    def test_already_ready_does_not_send(self):
        order = _order(status=CrmOrder.STATUS_READY)
        prep = crm_order_prep_datetime(order)
        refresh_order_late_prep(order.pk, prep + timedelta(minutes=15))
        self.assertEqual(self.calls, [])

    def test_not_yet_late_is_silent(self):
        order = _order()
        prep = crm_order_prep_datetime(order)
        refresh_order_late_prep(order.pk, prep - timedelta(minutes=1))
        self.assertEqual(self.calls, [])

    def test_when_ready_is_silent(self):
        order = _order(when_ready=True)
        refresh_order_late_prep(order.pk, datetime(2026, 10, 24, 20, 0, tzinfo=_TB))
        self.assertEqual(self.calls, [])

    def test_muted_cook_closes_existing_alert_without_edit(self):
        user = User.objects.create_user(username="vasya", password="password")
        profile = UserProfile.objects.create(user=user, internal_name="Вася Пупкин")
        order = _order()
        prep = crm_order_prep_datetime(order)
        refresh_order_late_prep(order.pk, prep + timedelta(minutes=15))
        order.taken_by = user
        order.status = CrmOrder.STATUS_CLIENT_APPROVED
        order.save(update_fields=["taken_by", "status", "updated_at"])
        profile.skip_late_alerts = True
        profile.save(update_fields=["skip_late_alerts"])
        self.calls.clear()
        refresh_order_late_prep(order.pk, prep + timedelta(minutes=20))
        self.assertEqual(self.calls, [])
        order.refresh_from_db()
        self.assertTrue(order.late_prep_closed)
        self.assertEqual(order.late_prep_message_id, 501)

    def test_deadline_moved_forward_deletes_message(self):
        order = _order()
        prep = crm_order_prep_datetime(order)
        refresh_order_late_prep(order.pk, prep + timedelta(minutes=15))
        order.time_start = time(21, 0)
        order.save(update_fields=["time_start", "updated_at"])
        self.calls.clear()
        refresh_order_late_prep(order.pk, prep + timedelta(minutes=15))
        self.assertEqual(self.calls, [("deleteMessage", {"chat_id": "crm-chat", "message_id": 501})])
        order.refresh_from_db()
        self.assertIsNone(order.late_prep_message_id)
        self.assertFalse(order.late_prep_closed)
        refresh_order_late_prep(order.pk, datetime(2026, 10, 24, 20, 40, tzinfo=_TB))
        self.assertEqual(self.calls[1][0], "sendMessage")
        self.assertIn("к 20:30", self.calls[1][1]["text"])

    def test_notify_scans_late_order(self):
        order = _order()
        prep = crm_order_prep_datetime(order)
        notify_late_preps(prep + timedelta(minutes=15))
        order.refresh_from_db()
        self.assertEqual(order.late_prep_message_id, 501)
        self.assertEqual(self.calls[0][0], "sendMessage")
