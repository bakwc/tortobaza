import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase, override_settings

from crm.models import CrmOrder, FlowwowWebhookEvent
from crm.tests.test_flowwow_orders import (
    _CARD_IMAGE,
    _CAKE_IMAGE,
    _SHOP_ID,
    _TOKEN,
    _flowwow_order,
    _image_response,
)

SECRET = "test-secret"
_VIEW_URL = "https://apis.flowwow.com/apiseller/orders/view"


def sign(body: bytes, secret: str = SECRET) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _view_response(item: dict) -> MagicMock:
    response = MagicMock()
    response.json.return_value = item
    response.raise_for_status = MagicMock()
    return response


@override_settings(
    FLOWWOW_WEBHOOK_SECRET=SECRET,
    FLOWWOW_API_TOKEN=_TOKEN,
    FLOWWOW_SHOP_ID=_SHOP_ID,
)
class FlowwowWebhookTests(TestCase):
    def setUp(self):
        self.view_calls: list[dict] = []
        self.image_calls: list[str] = []
        self.view_item = _flowwow_order(id=98765)
        self.view_error: BaseException | None = None
        get_patcher = patch("crm.flowwow.requests.get", side_effect=self._get)
        get_patcher.start()
        self.addCleanup(get_patcher.stop)
        schedule_patcher = patch("crm.flowwow.schedule_crm_order_telegram_sync")
        self.mock_schedule = schedule_patcher.start()
        self.addCleanup(schedule_patcher.stop)

    def _get(self, url, params=None, headers=None, timeout=None):
        if url == _VIEW_URL:
            if self.view_error is not None:
                raise self.view_error
            self.view_calls.append({"params": params, "headers": headers})
            return _view_response(self.view_item)
        self.image_calls.append(url)
        return _image_response()

    def _post(self, payload, signature=None):
        body = json.dumps(payload).encode("utf-8")
        headers = {}
        if signature is not False:
            headers["X-Webhook-Signature"] = sign(body) if signature is None else signature
        return self.client.post(
            "/api/webhooks/flowwow/",
            data=body,
            content_type="application/json",
            headers=headers,
        )

    def test_valid_signature_stores_event(self):
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440000",
            "event": "order.paid",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 1)
        self.assertEqual(
            FlowwowWebhookEvent.objects.get().uuid,
            "558e8b80-e29b-41dc-a716-446554440000",
        )

    def test_order_paid_fetches_view_and_creates_crm_order(self):
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440010",
            "event": "order.paid",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.view_calls), 1)
        call = self.view_calls[0]
        self.assertEqual(call["params"], {"shopId": 395006, "orderId": 98765})
        self.assertEqual(call["headers"]["Authorization"], "Bearer secret-token")
        self.assertEqual(call["headers"]["Accept"], "*/*")
        order = CrmOrder.objects.get(flowwow_order_id=98765)
        self.assertEqual(order.date.isoformat(), "2026-09-19")
        self.assertEqual(order.time_start.strftime("%H:%M"), "18:00")
        self.assertEqual(order.time_end.strftime("%H:%M"), "18:30")
        self.assertFalse(order.when_ready)
        self.assertEqual(order.contact, "kristina 595032371")
        self.assertEqual(
            order.delivery_address,
            "Sherif Khimshiashvili Street, 57; Orbi beach tower, room 1720",
        )
        self.assertEqual(order.fulfillment_type, CrmOrder.FULFILLMENT_DELIVERY)
        self.assertEqual(order.weight, "900 грамм")
        self.assertEqual(order.filling, "vanilla with strawberries")
        self.assertEqual(order.cake_price, Decimal("80.00"))
        self.assertEqual(order.prepayment, Decimal("80.00"))
        self.assertTrue(order.is_paid)
        self.assertEqual(order.payment_type, CrmOrder.PAYMENT_FLOWWOW)
        self.assertEqual(order.status, CrmOrder.STATUS_NEW)
        self.assertFalse(order.deleted)
        self.assertEqual(order.internal_description, "напишите, пожалуйста, на тортике надпись")
        self.assertIn("Flowwow #98765", order.description)
        images = list(order.images.order_by("position"))
        self.assertEqual([image.source_url for image in images], [_CAKE_IMAGE, _CARD_IMAGE])
        self.assertEqual(self.image_calls, [_CAKE_IMAGE, _CARD_IMAGE])
        self.mock_schedule.assert_called_once_with(order.pk)

    def test_order_paid_with_flowwow_new_creates_unconfirmed(self):
        self.view_item = _flowwow_order(id=98765, status=1)
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440012",
            "event": "order.paid",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        order = CrmOrder.objects.get(flowwow_order_id=98765)
        self.assertEqual(order.status, CrmOrder.STATUS_UNCONFIRMED)
        self.mock_schedule.assert_called_once_with(order.pk)

    def test_duplicate_uuid_does_not_create_second_row(self):
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440001",
            "event": "order.paid",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        first = self._post(payload)
        second = self._post(payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 1)
        self.assertEqual(CrmOrder.objects.filter(flowwow_order_id=98765).count(), 1)
        self.assertEqual(len(self.view_calls), 1)
        self.mock_schedule.assert_called_once()

    def test_order_cancelled_marks_crm_order_deleted(self):
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440011",
            "event": "order.cancelled",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.view_calls), 1)
        order = CrmOrder.objects.get(flowwow_order_id=98765)
        self.assertTrue(order.deleted)
        self.assertEqual(order.status, CrmOrder.STATUS_NEW)
        self.assertEqual(order.contact, "kristina 595032371")
        self.mock_schedule.assert_called_once_with(order.pk)

    def test_invalid_signature_returns_403(self):
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440002",
            "event": "order.paid",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        response = self._post(payload, signature="sha256=deadbeef")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 0)
        self.assertEqual(len(self.view_calls), 0)

    def test_missing_signature_returns_403(self):
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440003",
            "event": "order.paid",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        response = self._post(payload, signature=False)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 0)
        self.assertEqual(len(self.view_calls), 0)

    def test_invalid_json_returns_400(self):
        body = b"not-json"
        response = self.client.post(
            "/api/webhooks/flowwow/",
            data=body,
            content_type="application/json",
            headers={"X-Webhook-Signature": sign(body)},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 0)
        self.assertEqual(len(self.view_calls), 0)

    def test_missing_uuid_returns_400(self):
        payload = {
            "event": "order.paid",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 0)
        self.assertEqual(len(self.view_calls), 0)

    def test_test_event_without_order_returns_200(self):
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440004",
            "event": "test",
            "shopId": 1123,
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 1)
        self.assertEqual(
            FlowwowWebhookEvent.objects.get().uuid,
            "558e8b80-e29b-41dc-a716-446554440004",
        )
        self.assertEqual(len(self.view_calls), 0)
        self.assertEqual(CrmOrder.objects.count(), 0)
        self.mock_schedule.assert_not_called()

    def test_view_failure_does_not_store_uuid(self):
        self.view_error = requests.HTTPError("boom")
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440012",
            "event": "order.paid",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        with self.assertRaises(requests.HTTPError):
            self._post(payload)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 0)
        self.assertEqual(CrmOrder.objects.count(), 0)
        self.mock_schedule.assert_not_called()
