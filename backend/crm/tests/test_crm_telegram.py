import hashlib
import io
import json
import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import UserProfile
from crm.models import CrmOrder, CrmOrderImage, ResolvedYandexAddress, YandexAddressResolveFailure
from crm.telegram import (
    build_crm_order_telegram_html,
    build_crm_order_telegram_payload,
    crm_order_in_telegram_window,
    crm_order_slot_datetime,
    crm_order_telegram_hash,
    sync_crm_order_to_telegram,
)

_TB = ZoneInfo("Asia/Tbilisi")


class FakeHttpResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _jpeg(name: str) -> SimpleUploadedFile:
    buf = io.BytesIO()
    im = Image.new("RGB", (40, 40), color="pink")
    im.save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


@override_settings(
    TELEGRAM_BOT_TOKEN="bot-token",
    TELEGRAM_CHAT_ID="site-chat",
    TELEGRAM_CRM_CHAT_ID="crm-chat",
)
class CrmTelegramTests(TestCase):
    def setUp(self):
        self.calls = []
        self._next_id = 100
        self.urlopen_patcher = patch(
            "crm.telegram.urllib.request.urlopen",
            side_effect=self._urlopen,
        )
        self.urlopen_patcher.start()
        self.addCleanup(self.urlopen_patcher.stop)

    def _next_message_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def _urlopen(self, req, timeout=None):
        url = req.full_url
        method = url.rsplit("/", 1)[-1]
        content_type = req.headers.get("Content-type") or req.headers.get("Content-Type") or ""
        if content_type.startswith("application/json"):
            payload = json.loads(req.data.decode("utf-8"))
            chat_id = str(payload["chat_id"])
            self.calls.append({"method": method, "payload": payload, "chat_id": chat_id})
            if method == "deleteMessage":
                return FakeHttpResponse({"ok": True, "result": True})
            if method == "sendMediaGroup":
                raise AssertionError("sendMediaGroup must be multipart")
            mid = self._next_message_id()
            return FakeHttpResponse({"ok": True, "result": {"message_id": mid}})
        body = req.data
        chat_match = re.search(rb'name="chat_id"\r\n\r\n([^\r]+)', body)
        chat_id = chat_match.group(1).decode() if chat_match else ""
        self.calls.append({"method": method, "payload": None, "chat_id": chat_id})
        if method == "sendMediaGroup":
            n = body.count(b'filename="')
            ids = [self._next_message_id() for _ in range(n)]
            return FakeHttpResponse({"ok": True, "result": [{"message_id": i} for i in ids]})
        mid = self._next_message_id()
        return FakeHttpResponse({"ok": True, "result": {"message_id": mid}})

    def _slot(self, delta: timedelta):
        point = timezone.now().astimezone(_TB) + delta
        return point.date(), point.time().replace(microsecond=0)

    def _create_order(self, *, delta: timedelta, **kwargs) -> CrmOrder:
        d, t = self._slot(delta)
        defaults = {
            "date": d,
            "time_start": t,
            "contact": "Customer",
            "nickname": "@nick",
            "delivery_address": "Rustaveli 1",
            "fulfillment_type": CrmOrder.FULFILLMENT_DELIVERY,
            "weight": "2kg",
            "filling": "Vanilla",
            "description": "Note",
            "cake_price": Decimal("120.00"),
            "prepayment": Decimal("30.00"),
            "is_paid": False,
            "payment_type": CrmOrder.PAYMENT_CASH,
        }
        defaults.update(kwargs)
        return CrmOrder.objects.create(**defaults)

    def test_outside_future_window_does_not_post(self):
        now_tb = timezone.now().astimezone(_TB)
        order = self._create_order(
            delta=timedelta(hours=2),
            date=now_tb.date() + timedelta(days=2),
        )
        sync_crm_order_to_telegram(order.pk)
        self.assertEqual(self.calls, [])
        order.refresh_from_db()
        self.assertIsNone(order.telegram_message_id)

    def test_next_calendar_day_before_16_does_not_post(self):
        now_tb = timezone.now().astimezone(_TB)
        frozen = datetime.combine(now_tb.date(), time(15, 59), tzinfo=_TB)
        order = self._create_order(
            delta=timedelta(hours=2),
            date=now_tb.date() + timedelta(days=1),
            time_start=time(23, 0),
            time_end=None,
        )
        with patch("crm.telegram.timezone.now", return_value=frozen):
            sync_crm_order_to_telegram(order.pk)
        self.assertEqual(self.calls, [])
        order.refresh_from_db()
        self.assertIsNone(order.telegram_message_id)

    def test_next_calendar_day_from_16_posts(self):
        now_tb = timezone.now().astimezone(_TB)
        frozen = datetime.combine(now_tb.date(), time(16, 0), tzinfo=_TB)
        order = self._create_order(
            delta=timedelta(hours=2),
            date=now_tb.date() + timedelta(days=1),
            time_start=time(23, 0),
            time_end=None,
        )
        with patch("crm.telegram.timezone.now", return_value=frozen):
            sync_crm_order_to_telegram(order.pk)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["method"], "sendMessage")

    def test_within_window_posts_to_crm_chat(self):
        order = self._create_order(delta=timedelta(hours=2))
        sync_crm_order_to_telegram(order.pk)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["method"], "sendMessage")
        self.assertEqual(self.calls[0]["chat_id"], "crm-chat")
        self.assertNotEqual(self.calls[0]["chat_id"], "site-chat")
        order.refresh_from_db()
        self.assertIsNotNone(order.telegram_message_id)
        html = self.calls[0]["payload"]["text"]
        self.assertIn("Customer", html)
        self.assertIn("Vanilla", html)
        self.assertIn("2kg", html)
        self.assertEqual(order.telegram_payload_hash, crm_order_telegram_hash(order))

    def test_past_within_seven_days_posts(self):
        order = self._create_order(delta=timedelta(days=-3))
        sync_crm_order_to_telegram(order.pk)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["method"], "sendMessage")

    def test_older_than_seven_days_does_not_post(self):
        order = self._create_order(delta=timedelta(days=-8))
        sync_crm_order_to_telegram(order.pk)
        self.assertEqual(self.calls, [])
        order.refresh_from_db()
        self.assertIsNone(order.telegram_message_id)

    def test_explicit_midnight_slot_is_end_of_specified_day(self):
        order = self._create_order(
            delta=timedelta(hours=2),
            date=date(2026, 8, 28),
            time_start=time(0, 0),
            time_end=None,
        )
        self.assertEqual(
            crm_order_slot_datetime(order),
            datetime(2026, 8, 29, 0, 0, tzinfo=_TB),
        )

    def test_missing_time_slot_stays_start_of_specified_day(self):
        order = self._create_order(
            delta=timedelta(hours=2),
            date=date(2026, 8, 28),
            time_start=None,
            time_end=None,
        )
        self.assertEqual(
            crm_order_slot_datetime(order),
            datetime(2026, 8, 28, 0, 0, tzinfo=_TB),
        )

    def test_seven_day_window_includes_midnight_order_from_seven_days_ago(self):
        frozen = datetime(2026, 8, 28, 16, 53, tzinfo=_TB)
        order = self._create_order(
            delta=timedelta(hours=2),
            date=date(2026, 8, 21),
            time_start=time(0, 0),
            time_end=None,
        )
        self.assertTrue(crm_order_in_telegram_window(order, frozen))
        with patch("crm.telegram.timezone.now", return_value=frozen):
            sync_crm_order_to_telegram(order.pk)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["method"], "sendMessage")

    def test_today_midnight_posts_before_16(self):
        now_tb = timezone.now().astimezone(_TB)
        frozen = datetime.combine(now_tb.date(), time(15, 59), tzinfo=_TB)
        order = self._create_order(
            delta=timedelta(hours=2),
            date=now_tb.date(),
            time_start=time(0, 0),
            time_end=None,
        )
        with patch("crm.telegram.timezone.now", return_value=frozen):
            sync_crm_order_to_telegram(order.pk)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["method"], "sendMessage")

    def test_second_sync_without_changes_skips_http(self):
        order = self._create_order(delta=timedelta(hours=2))
        sync_crm_order_to_telegram(order.pk)
        self.calls.clear()
        sync_crm_order_to_telegram(order.pk)
        self.assertEqual(self.calls, [])

    def test_is_paid_change_edits_message(self):
        order = self._create_order(delta=timedelta(hours=2))
        sync_crm_order_to_telegram(order.pk)
        self.calls.clear()
        order.is_paid = True
        order.save(update_fields=["is_paid", "updated_at"])
        sync_crm_order_to_telegram(order.pk)
        methods = [c["method"] for c in self.calls]
        self.assertEqual(methods, ["editMessageText"])
        self.assertIn("Оплачен:</b> да", self.calls[0]["payload"]["text"])

    def test_taken_by_telegram_nick_in_html_and_edits(self):
        chef = User.objects.create_user(username="chef", password="password")
        UserProfile.objects.create(user=chef, telegram_username="chef_anna")
        order = self._create_order(delta=timedelta(hours=2))
        sync_crm_order_to_telegram(order.pk)
        html = build_crm_order_telegram_html(order)
        self.assertNotIn("Готовит шеф", html)
        self.calls.clear()
        order.taken_by = chef
        order.save(update_fields=["taken_by", "updated_at"])
        html = build_crm_order_telegram_html(order)
        self.assertIn('Готовит шеф</b> <a href="https://t.me/chef_anna">@chef_anna</a>', html)
        sync_crm_order_to_telegram(order.pk)
        methods = [c["method"] for c in self.calls]
        self.assertEqual(methods, ["editMessageText"])
        self.assertIn("@chef_anna", self.calls[0]["payload"]["text"])

    def test_taken_by_falls_back_to_username_without_link(self):
        chef = User.objects.create_user(username="site_chef", password="password")
        order = self._create_order(delta=timedelta(hours=2), taken_by=chef)
        html = build_crm_order_telegram_html(order)
        self.assertIn("Готовит шеф</b> site_chef", html)
        self.assertNotIn("t.me", html)

    def test_slot_change_edits_and_replies(self):
        order = self._create_order(delta=timedelta(hours=2))
        sync_crm_order_to_telegram(order.pk)
        original_id = CrmOrder.objects.get(pk=order.pk).telegram_message_id
        self.calls.clear()
        new_date, new_time = self._slot(timedelta(hours=5))
        order.date = new_date
        order.time_start = new_time
        order.save(update_fields=["date", "time_start", "updated_at"])
        sync_crm_order_to_telegram(order.pk)
        methods = [c["method"] for c in self.calls]
        self.assertEqual(methods, ["editMessageText", "sendMessage"])
        reply = self.calls[1]["payload"]
        self.assertEqual(reply["reply_to_message_id"], original_id)
        self.assertIn("время доставки / выдачи поменялось на", reply["text"])
        self.assertIn("исходное сообщение", reply["text"])

    def test_posted_order_moved_beyond_horizon_still_edits(self):
        order = self._create_order(delta=timedelta(hours=2))
        sync_crm_order_to_telegram(order.pk)
        self.calls.clear()
        new_date, new_time = self._slot(timedelta(days=5))
        order.date = new_date
        order.time_start = new_time
        order.save(update_fields=["date", "time_start", "updated_at"])
        sync_crm_order_to_telegram(order.pk)
        methods = [c["method"] for c in self.calls]
        self.assertEqual(methods, ["editMessageText", "sendMessage"])
        order.refresh_from_db()
        self.assertEqual(order.telegram_posted_date, new_date)

    def test_delete_after_post_edits_cancelled(self):
        order = self._create_order(delta=timedelta(hours=2))
        sync_crm_order_to_telegram(order.pk)
        self.calls.clear()
        order.deleted = True
        order.save(update_fields=["deleted", "updated_at"])
        sync_crm_order_to_telegram(order.pk)
        self.assertEqual([c["method"] for c in self.calls], ["editMessageText"])
        self.assertIn("ОТМЕНЁН", self.calls[0]["payload"]["text"])

    def test_deleted_unposted_does_not_post(self):
        order = self._create_order(delta=timedelta(hours=2), deleted=True)
        sync_crm_order_to_telegram(order.pk)
        self.assertEqual(self.calls, [])

    def test_command_posts_unposted_in_window(self):
        posted = self._create_order(delta=timedelta(hours=2))
        posted.telegram_message_id = 1
        posted.telegram_payload_hash = crm_order_telegram_hash(posted)
        posted.telegram_posted_date = posted.date
        posted.telegram_posted_time_start = posted.time_start
        posted.telegram_posted_time_end = posted.time_end
        posted.save(
            update_fields=[
                "telegram_message_id",
                "telegram_payload_hash",
                "telegram_posted_date",
                "telegram_posted_time_start",
                "telegram_posted_time_end",
            ]
        )
        pending = self._create_order(delta=timedelta(hours=3))
        fake_response = MagicMock()
        fake_response.output_text = "https://yandex.com/maps/?text=Rustaveli"
        with patch("crm.yandex_maps.OpenAI") as openai_cls:
            openai_cls.return_value.responses.create.return_value = fake_response
            call_command("sync_crm_orders_to_telegram")
        pending.refresh_from_db()
        self.assertIsNotNone(pending.telegram_message_id)
        methods = [c["method"] for c in self.calls]
        self.assertEqual(methods, ["editMessageText", "sendMessage"])

    def test_single_photo_uses_send_photo(self):
        order = self._create_order(delta=timedelta(hours=2))
        CrmOrderImage.objects.create(order=order, image=_jpeg("one.jpg"), position=0)
        sync_crm_order_to_telegram(order.pk)
        methods = [c["method"] for c in self.calls]
        self.assertEqual(methods, ["sendPhoto", "sendMessage"])
        self.assertEqual(self.calls[0]["chat_id"], "crm-chat")
        order.refresh_from_db()
        self.assertEqual(len(order.telegram_media_ids), 1)

    def test_multiple_photos_uses_media_group(self):
        order = self._create_order(delta=timedelta(hours=2))
        CrmOrderImage.objects.create(order=order, image=_jpeg("a.jpg"), position=0)
        CrmOrderImage.objects.create(order=order, image=_jpeg("b.jpg"), position=1)
        sync_crm_order_to_telegram(order.pk)
        methods = [c["method"] for c in self.calls]
        self.assertEqual(methods, ["sendMediaGroup", "sendMessage"])
        order.refresh_from_db()
        self.assertEqual(len(order.telegram_media_ids), 2)

    def test_no_photos_sends_text_only(self):
        order = self._create_order(delta=timedelta(hours=2))
        sync_crm_order_to_telegram(order.pk)
        self.assertEqual([c["method"] for c in self.calls], ["sendMessage"])

    def test_skips_when_settings_empty(self):
        order = self._create_order(delta=timedelta(hours=2))
        with override_settings(TELEGRAM_BOT_TOKEN="", TELEGRAM_CRM_CHAT_ID="crm-chat"):
            sync_crm_order_to_telegram(order.pk)
        self.assertEqual(self.calls, [])

    def test_html_contains_useful_fields(self):
        order = self._create_order(delta=timedelta(hours=2), is_delivered=True, is_paid=True)
        text = build_crm_order_telegram_html(order)
        self.assertIn("Доставка", text)
        self.assertIn("Оплачен:</b> да", text)
        self.assertIn("Доставлен / выдан:</b> ✅", text)
        self.assertIn(
            f"https://sweet-chill.ge/ru/crm?date={order.date.isoformat()}&amp;order={order.pk}",
            text,
        )
        self.assertIn(f"https://sweet-chill.ge/ru/crm/{order.pk}/edit", text)
        self.assertIn(">смотреть</a>", text)
        self.assertIn(">редактировать</a>", text)
        self.assertIn("<b>Адрес:</b> Rustaveli 1", text)
        self.assertIn("<b>Контакт:</b> Customer", text)
        self.assertNotIn("WhatsApp", text)
        self.assertNotIn("wa.me", text)
        self.assertNotIn("t.me", text)

    def test_html_undelivered_uses_red_mark(self):
        order = self._create_order(delta=timedelta(hours=2), is_delivered=False)
        text = build_crm_order_telegram_html(order)
        self.assertIn("Доставлен / выдан:</b> ❌", text)
        self.assertIn(f"https://sweet-chill.ge/ru/crm/{order.pk}/take", text)
        self.assertIn(">взять в работу</a>", text)

    def test_html_delivered_omits_take_in_work_link(self):
        order = self._create_order(delta=timedelta(hours=2), is_delivered=True)
        text = build_crm_order_telegram_html(order)
        self.assertNotIn("/take", text)
        self.assertNotIn("взять в работу", text)

    def test_stale_hash_without_take_url_edits_message(self):
        order = self._create_order(delta=timedelta(hours=2))
        sync_crm_order_to_telegram(order.pk)
        self.calls.clear()
        payload = build_crm_order_telegram_payload(order)
        payload.pop("take_in_work_url")
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        order.telegram_payload_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        order.save(update_fields=["telegram_payload_hash", "updated_at"])
        sync_crm_order_to_telegram(order.pk)
        self.assertEqual([c["method"] for c in self.calls], ["editMessageText"])
        self.assertIn("взять в работу", self.calls[0]["payload"]["text"])

    def test_html_adds_e164_and_whatsapp_for_phone_contact(self):
        order = self._create_order(delta=timedelta(hours=2), contact="+7 916 123 45 67 Иван")
        text = build_crm_order_telegram_html(order)
        self.assertIn("<b>Контакт:</b> +7 916 123 45 67 Иван", text)
        self.assertIn("+79161234567", text)
        self.assertIn('<a href="https://wa.me/79161234567">WhatsApp</a>', text)
        self.assertNotIn("t.me", text)
        self.assertNotIn("tel:", text)

    def test_when_ready_html(self):
        order = self._create_order(delta=timedelta(hours=2), time_start=None, when_ready=True)
        text = build_crm_order_telegram_html(order)
        self.assertIn("по готовности", text)
        self.assertNotIn("время не указано", text)

    def test_when_ready_slot_change_from_unknown_replies(self):
        order = self._create_order(delta=timedelta(hours=2), time_start=None)
        sync_crm_order_to_telegram(order.pk)
        original_id = CrmOrder.objects.get(pk=order.pk).telegram_message_id
        self.calls.clear()
        order.when_ready = True
        order.save(update_fields=["when_ready", "updated_at"])
        sync_crm_order_to_telegram(order.pk)
        methods = [c["method"] for c in self.calls]
        self.assertEqual(methods, ["editMessageText", "sendMessage"])
        reply = self.calls[1]["payload"]
        self.assertEqual(reply["reply_to_message_id"], original_id)
        self.assertIn("по готовности", reply["text"])

    def test_create_api_schedules_sync(self):
        user = User.objects.create_user(username="admin", password="password", is_staff=True)
        client = APIClient()
        client.force_authenticate(user=user)
        d, t = self._slot(timedelta(hours=2))
        with patch("crm.views.schedule_crm_order_telegram_sync") as scheduled:
            response = client.post(
                "/api/crm/orders/",
                {
                    "date": d.isoformat(),
                    "time_start": t.strftime("%H:%M:%S"),
                    "contact": "Customer",
                    "delivery_address": "Addr",
                    "fulfillment_type": "delivery",
                    "weight": "1kg",
                    "filling": "Choco",
                    "cake_price": "50.00",
                    "prepayment": "10.00",
                    "is_paid": False,
                    "payment_type": "cash",
                },
            )
        self.assertEqual(response.status_code, 201)
        scheduled.assert_called_once_with(response.json()["id"])
        self.assertNotIn("telegram_message_id", response.json())

    def test_html_uses_yandex_link_when_cached(self):
        order = self._create_order(delta=timedelta(hours=2))
        ResolvedYandexAddress.objects.create(
            address="Rustaveli 1",
            yandex_url="https://yandex.com/maps/?text=Rustaveli",
        )
        text = build_crm_order_telegram_html(order)
        self.assertIn(
            '<b>Адрес:</b> <a href="https://yandex.com/maps/?text=Rustaveli">Rustaveli 1</a>',
            text,
        )

    def test_command_resolves_uncached_delivery_address(self):
        posted = self._create_order(delta=timedelta(hours=2))
        posted.telegram_message_id = 1
        posted.telegram_payload_hash = crm_order_telegram_hash(posted)
        posted.telegram_posted_date = posted.date
        posted.telegram_posted_time_start = posted.time_start
        posted.telegram_posted_time_end = posted.time_end
        posted.save(
            update_fields=[
                "telegram_message_id",
                "telegram_payload_hash",
                "telegram_posted_date",
                "telegram_posted_time_start",
                "telegram_posted_time_end",
            ]
        )
        fake_response = MagicMock()
        fake_response.output_text = "https://yandex.com/maps/?text=Rustaveli"
        with patch("crm.yandex_maps.OpenAI") as openai_cls:
            openai_cls.return_value.responses.create.return_value = fake_response
            call_command("sync_crm_orders_to_telegram")
        cached = ResolvedYandexAddress.objects.get(address="Rustaveli 1")
        self.assertEqual(cached.yandex_url, "https://yandex.com/maps/?text=Rustaveli")
        self.assertEqual([c["method"] for c in self.calls], ["editMessageText"])
        self.assertIn(
            '<a href="https://yandex.com/maps/?text=Rustaveli">Rustaveli 1</a>',
            self.calls[0]["payload"]["text"],
        )
        self.calls.clear()
        with patch("crm.yandex_maps.OpenAI") as openai_cls:
            call_command("sync_crm_orders_to_telegram")
            openai_cls.assert_not_called()
        self.assertEqual(self.calls, [])

    def test_command_skips_cached_address(self):
        ResolvedYandexAddress.objects.create(
            address="Rustaveli 1",
            yandex_url="https://yandex.com/maps/?text=Rustaveli",
        )
        self._create_order(delta=timedelta(hours=2))
        with patch("crm.yandex_maps.OpenAI") as openai_cls:
            call_command("sync_crm_orders_to_telegram")
            openai_cls.assert_not_called()

    def test_command_does_not_resolve_pickup_empty_deleted_or_outside_window(self):
        self._create_order(
            delta=timedelta(hours=2),
            fulfillment_type=CrmOrder.FULFILLMENT_PICKUP,
            delivery_address="Pickup Street",
        )
        self._create_order(delta=timedelta(hours=2), delivery_address="")
        self._create_order(delta=timedelta(hours=2), deleted=True, delivery_address="Deleted Street")
        self._create_order(delta=timedelta(days=-8), delivery_address="Old Street")
        with patch("crm.yandex_maps.OpenAI") as openai_cls:
            call_command("sync_crm_orders_to_telegram")
            openai_cls.assert_not_called()

    def test_command_unpublished_send_includes_yandex_link(self):
        self._create_order(delta=timedelta(hours=2))
        fake_response = MagicMock()
        fake_response.output_text = "https://yandex.com/maps/?text=Rustaveli"
        with patch("crm.yandex_maps.OpenAI") as openai_cls:
            openai_cls.return_value.responses.create.return_value = fake_response
            call_command("sync_crm_orders_to_telegram")
        self.assertEqual(self.calls[0]["method"], "sendMessage")
        self.assertIn(
            '<a href="https://yandex.com/maps/?text=Rustaveli">Rustaveli 1</a>',
            self.calls[0]["payload"]["text"],
        )

    def test_command_resolve_failure_increments_and_stops_after_three(self):
        order = self._create_order(delta=timedelta(hours=2))
        with patch("crm.yandex_maps.OpenAI") as openai_cls:
            openai_cls.return_value.responses.create.side_effect = RuntimeError("down")
            call_command("sync_crm_orders_to_telegram")
        failure = YandexAddressResolveFailure.objects.get(address="Rustaveli 1")
        self.assertEqual(failure.failure_count, 1)
        order.refresh_from_db()
        self.assertIsNotNone(order.telegram_message_id)
        for expected in (2, 3):
            with patch("crm.yandex_maps.OpenAI") as openai_cls:
                openai_cls.return_value.responses.create.side_effect = RuntimeError("down")
                call_command("sync_crm_orders_to_telegram")
            failure.refresh_from_db()
            self.assertEqual(failure.failure_count, expected)
        self.calls.clear()
        with patch("crm.yandex_maps.OpenAI") as openai_cls:
            call_command("sync_crm_orders_to_telegram")
            openai_cls.assert_not_called()
        self.assertEqual(self.calls, [])

    def test_command_one_address_fails_other_resolves(self):
        self._create_order(delta=timedelta(hours=2), delivery_address="Bad Addr")
        self._create_order(delta=timedelta(hours=3), delivery_address="Good Addr")

        def fake_create(*, prompt, input):
            if input == "Bad Addr":
                raise RuntimeError("down")
            fake_response = MagicMock()
            fake_response.output_text = "https://yandex.com/maps/?text=Good"
            return fake_response

        with patch("crm.yandex_maps.OpenAI") as openai_cls:
            openai_cls.return_value.responses.create.side_effect = fake_create
            call_command("sync_crm_orders_to_telegram")
        self.assertEqual(
            YandexAddressResolveFailure.objects.get(address="Bad Addr").failure_count,
            1,
        )
        cached = ResolvedYandexAddress.objects.get(address="Good Addr")
        self.assertEqual(cached.yandex_url, "https://yandex.com/maps/?text=Good")

    def test_command_success_deletes_failure_row(self):
        YandexAddressResolveFailure.objects.create(address="Rustaveli 1", failure_count=2)
        self._create_order(delta=timedelta(hours=2))
        fake_response = MagicMock()
        fake_response.output_text = "https://yandex.com/maps/?text=Rustaveli"
        with patch("crm.yandex_maps.OpenAI") as openai_cls:
            openai_cls.return_value.responses.create.return_value = fake_response
            call_command("sync_crm_orders_to_telegram")
        self.assertFalse(YandexAddressResolveFailure.objects.filter(address="Rustaveli 1").exists())

    def test_struck_out_address_can_still_resolve_via_api(self):
        YandexAddressResolveFailure.objects.create(address="Rustaveli 1", failure_count=3)
        self._create_order(delta=timedelta(hours=2))
        with patch("crm.yandex_maps.OpenAI") as openai_cls:
            call_command("sync_crm_orders_to_telegram")
            openai_cls.assert_not_called()
        user = User.objects.create_user(username="worker", password="password")
        client = APIClient()
        client.force_authenticate(user=user)
        fake_response = MagicMock()
        fake_response.output_text = "https://yandex.com/maps/?text=Rustaveli"
        with patch("crm.yandex_maps.OpenAI") as openai_cls:
            openai_cls.return_value.responses.create.return_value = fake_response
            response = client.post(
                "/api/crm/resolve-yandex-address/",
                {"address": "Rustaveli 1"},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ResolvedYandexAddress.objects.get(address="Rustaveli 1").yandex_url,
            "https://yandex.com/maps/?text=Rustaveli",
        )
