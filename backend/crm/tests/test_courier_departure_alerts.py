from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from accounts.models import UserProfile
from crm.courier_alerts import notify_courier_departures
from crm.models import CrmOrder

_TB = ZoneInfo("Asia/Tbilisi")
_NOW = datetime(2026, 10, 24, 12, 10, tzinfo=_TB)


def _order(**kwargs) -> CrmOrder:
    fields = {
        "date": date(2026, 10, 24),
        "time_start": time(13, 0),
        "time_end": time(14, 0),
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


def _courier(username: str, active: bool, key: str) -> UserProfile:
    user = User.objects.create_user(username=username, password="password")
    return UserProfile.objects.create(
        user=user,
        is_active_courier=active,
        bark_device_key=key,
    )


@override_settings(SITE_URL="https://sweet-chill.ge")
class NotifyCourierDeparturesTests(TestCase):
    def setUp(self):
        self.post_patcher = patch("crm.courier_alerts.requests.post")
        self.post = self.post_patcher.start()
        self.addCleanup(self.post_patcher.stop)
        self.response = MagicMock()
        self.post.return_value = self.response

    def test_window_sends_alarm_to_each_active_courier(self):
        order = _order()
        _courier("one", True, "key-one")
        _courier("two", True, "key-two")
        _courier("off", False, "key-off")
        _courier("empty", True, "")

        notify_courier_departures(_NOW)

        self.assertEqual(self.post.call_count, 2)
        keys = set()
        for call in self.post.call_args_list:
            self.assertEqual(call.args[0], "https://api.day.app/push")
            self.assertEqual(call.kwargs["timeout"], 20)
            payload = call.kwargs["json"]
            keys.add(payload["device_key"])
            self.assertEqual(payload["sound"], "alarm")
            self.assertEqual(payload["title"], "Выезд через 20 мин")
            self.assertEqual(
                payload["url"],
                f"https://sweet-chill.ge/ru/crm?date=2026-10-24&order={order.pk}",
            )
            self.assertEqual(
                payload["body"],
                "\n".join(
                    [
                        f"Заказ #{order.pk}",
                        "Адрес: Rustaveli 1",
                        "Выезд: 12:30",
                        "Доставка: 13:00 – 14:00",
                    ]
                ),
            )
        self.assertEqual(keys, {"key-one", "key-two"})
        self.response.raise_for_status.assert_called()

    def test_same_departure_is_sent_on_every_sync(self):
        _order()
        _courier("one", True, "key-one")

        notify_courier_departures(_NOW)
        self.post.reset_mock()
        notify_courier_departures(_NOW)

        self.assertEqual(self.post.call_count, 1)
        payload = self.post.call_args.kwargs["json"]
        self.assertEqual(payload["device_key"], "key-one")
        self.assertEqual(payload["title"], "Выезд через 20 мин")

    def test_shifted_departure_sends_updated_time(self):
        order = _order()
        _courier("one", True, "key-one")
        notify_courier_departures(_NOW)
        order.delivery_duration_seconds = 20 * 60
        order.save(update_fields=["delivery_duration_seconds", "updated_at"])
        self.post.reset_mock()

        notify_courier_departures(_NOW)

        self.assertEqual(self.post.call_count, 1)
        payload = self.post.call_args.kwargs["json"]
        self.assertIn("Выезд: 12:20", payload["body"])
        self.assertEqual(payload["title"], "Выезд через 10 мин")

    def test_outside_window_is_silent(self):
        _order()
        _courier("one", True, "key-one")

        notify_courier_departures(_NOW - timedelta(minutes=1))
        notify_courier_departures(datetime(2026, 10, 24, 18, 30, tzinfo=_TB))

        self.post.assert_not_called()

    def test_overdue_not_in_delivery_sends_for_six_hours(self):
        _order()
        _courier("one", True, "key-one")

        notify_courier_departures(datetime(2026, 10, 24, 12, 30, tzinfo=_TB))

        self.assertEqual(self.post.call_args.kwargs["json"]["title"], "Выезд просрочен")
        self.post.reset_mock()
        _order()
        notify_courier_departures(datetime(2026, 10, 24, 18, 29, tzinfo=_TB))

        self.assertEqual(self.post.call_count, 2)
        for call in self.post.call_args_list:
            self.assertEqual(call.kwargs["json"]["title"], "Выезд просрочен")

    def test_pickup_when_ready_and_in_delivery_are_silent(self):
        _order(fulfillment_type=CrmOrder.FULFILLMENT_PICKUP)
        _order(when_ready=True, time_start=None, time_end=None)
        _order(status=CrmOrder.STATUS_IN_DELIVERY)
        _courier("one", True, "key-one")

        notify_courier_departures(_NOW)

        self.post.assert_not_called()

    def test_without_active_courier_key_is_silent(self):
        _order()
        _courier("off", False, "key-off")
        _courier("empty", True, "")

        notify_courier_departures(_NOW)

        self.post.assert_not_called()
