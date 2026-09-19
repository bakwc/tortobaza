import hashlib
import hmac
import json

from django.test import TestCase, override_settings

from crm.models import FlowwowWebhookEvent

SECRET = "test-secret"


def sign(body: bytes, secret: str = SECRET) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@override_settings(FLOWWOW_WEBHOOK_SECRET=SECRET)
class FlowwowWebhookTests(TestCase):
    def test_valid_signature_stores_event(self):
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440000",
            "event": "order.paid",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        body = json.dumps(payload).encode("utf-8")
        response = self.client.post(
            "/api/webhooks/flowwow/",
            data=body,
            content_type="application/json",
            headers={"X-Webhook-Signature": sign(body)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 1)
        self.assertEqual(
            FlowwowWebhookEvent.objects.get().uuid,
            "558e8b80-e29b-41dc-a716-446554440000",
        )

    def test_duplicate_uuid_does_not_create_second_row(self):
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440001",
            "event": "order.paid",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"X-Webhook-Signature": sign(body)}
        first = self.client.post(
            "/api/webhooks/flowwow/",
            data=body,
            content_type="application/json",
            headers=headers,
        )
        second = self.client.post(
            "/api/webhooks/flowwow/",
            data=body,
            content_type="application/json",
            headers=headers,
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 1)

    def test_invalid_signature_returns_403(self):
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440002",
            "event": "order.paid",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        body = json.dumps(payload).encode("utf-8")
        response = self.client.post(
            "/api/webhooks/flowwow/",
            data=body,
            content_type="application/json",
            headers={"X-Webhook-Signature": "sha256=deadbeef"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 0)

    def test_missing_signature_returns_403(self):
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440003",
            "event": "order.paid",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        body = json.dumps(payload).encode("utf-8")
        response = self.client.post(
            "/api/webhooks/flowwow/",
            data=body,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 0)

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

    def test_missing_uuid_returns_400(self):
        payload = {
            "event": "order.paid",
            "shopId": 1123,
            "order": {"id": 98765},
        }
        body = json.dumps(payload).encode("utf-8")
        response = self.client.post(
            "/api/webhooks/flowwow/",
            data=body,
            content_type="application/json",
            headers={"X-Webhook-Signature": sign(body)},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 0)

    def test_test_event_without_order_returns_200(self):
        payload = {
            "uuid": "558e8b80-e29b-41dc-a716-446554440004",
            "event": "test",
            "shopId": 1123,
        }
        body = json.dumps(payload).encode("utf-8")
        response = self.client.post(
            "/api/webhooks/flowwow/",
            data=body,
            content_type="application/json",
            headers={"X-Webhook-Signature": sign(body)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FlowwowWebhookEvent.objects.count(), 1)
        self.assertEqual(
            FlowwowWebhookEvent.objects.get().uuid,
            "558e8b80-e29b-41dc-a716-446554440004",
        )
