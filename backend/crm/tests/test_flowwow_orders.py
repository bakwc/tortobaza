import io
from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import requests
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from crm.flowwow import _filling, _weight
from crm.models import CrmOrder, CrmOrderImage

_TB = ZoneInfo("Asia/Tbilisi")
_NOW = datetime(2026, 9, 19, 15, 0, tzinfo=_TB)
_TOKEN = "secret-token"
_SHOP_ID = "395006"
_CAKE_IMAGE = "https://content2.flowwow-images.com/data/flowers/1000x1000/43/cake.jpg"
_CARD_IMAGE = "https://content2.flowwow-images.com/data/flowers/1000x1000/62/card.jpg"
_OTHER_IMAGE = "https://content2.flowwow-images.com/data/flowers/1000x1000/06/other.jpg"


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), color="pink").save(buf, format="JPEG")
    return buf.getvalue()


def _jpeg_file(name: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, _jpeg_bytes(), content_type="image/jpeg")


def _ts(value: datetime) -> int:
    return int(value.timestamp())


def _flowwow_order(**overrides) -> dict:
    item = {
        "id": 25836184,
        "shopId": 395006,
        "createdDate": _ts(datetime(2026, 9, 18, 16, 0, tzinfo=_TB)),
        "status": 2,
        "price": "2009.00",
        "products": [
            {
                "productId": 76014182,
                "type": 1,
                "name": "Бенто торт 900 грамм С ВАШЕЙ НАДПИСЬЮ",
                "price": "80.00",
                "count": 1,
                "images": [_CAKE_IMAGE],
                "selectedProperties": [
                    {
                        "propertyId": 45,
                        "propertyTitle": "Filling",
                        "valueId": 319,
                        "valueTitle": "vanilla with strawberries",
                    }
                ],
            },
            {
                "productId": 35728,
                "type": 3,
                "name": "Открытка",
                "price": "0.00",
                "count": 1,
                "images": [_CARD_IMAGE],
                "selectedProperties": [],
            },
        ],
        "deliveryType": 1,
        "deliveryTimeType": 2,
        "deliveryDateFrom": _ts(datetime(2026, 9, 19, 18, 0, tzinfo=_TB)),
        "deliveryDateTo": _ts(datetime(2026, 9, 19, 18, 30, tzinfo=_TB)),
        "address": "Sherif Khimshiashvili Street, 57; Orbi beach tower, room 1720",
        "courierInfo": "Orbi beach tower, комната 1720",
        "shopAdditionalInfo": "напишите, пожалуйста, на тортике надпись",
        "message": "с днем рождения",
        "comment": "оставить у двери",
        "user": {"name": "Саша", "phone": "447472003498"},
        "recipient": {"name": "kristina", "phone": "595032371"},
    }
    item.update(overrides)
    return item


def _list_response(items: list[dict], total: int | None = None) -> MagicMock:
    response = MagicMock()
    response.json.return_value = {"items": items, "total": total if total is not None else len(items)}
    response.raise_for_status = MagicMock()
    return response


def _image_response() -> MagicMock:
    response = MagicMock()
    response.content = _jpeg_bytes()
    response.raise_for_status = MagicMock()
    return response


@override_settings(FLOWWOW_API_TOKEN=_TOKEN, FLOWWOW_SHOP_ID=_SHOP_ID)
class FlowwowOrderSyncTests(TestCase):
    def setUp(self):
        self.list_calls: list[dict] = []
        self.image_calls: list[str] = []
        self.items: list[dict] = []

    def _get(self, url, params=None, headers=None, timeout=None):
        if url == "https://apis.flowwow.com/apiseller/orders/list":
            self.list_calls.append({"params": params, "headers": headers})
            return _list_response(self.items)
        self.image_calls.append(url)
        return _image_response()

    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_fetches_list_with_shop_id_and_bearer(self, mock_get, _mock_now):
        self.items = [_flowwow_order(id=1), _flowwow_order(id=2)]
        mock_get.side_effect = self._get
        from crm.flowwow import sync_flowwow_orders

        sync_flowwow_orders()
        self.assertEqual(len(self.list_calls), 1)
        call = self.list_calls[0]
        self.assertEqual(call["params"], {"shopId": 395006})
        self.assertEqual(call["headers"]["Authorization"], "Bearer secret-token")
        self.assertEqual(call["headers"]["Accept"], "*/*")
        self.assertEqual(
            set(CrmOrder.objects.values_list("flowwow_order_id", flat=True)),
            {1, 2},
        )

    @override_settings(FLOWWOW_API_TOKEN='"secret-token"', FLOWWOW_SHOP_ID='"395006"')
    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_strips_quoted_systemd_env_values(self, mock_get, _mock_now):
        self.items = [_flowwow_order(id=1)]
        mock_get.side_effect = self._get
        from crm.flowwow import sync_flowwow_orders

        sync_flowwow_orders()
        call = self.list_calls[0]
        self.assertEqual(call["params"]["shopId"], 395006)
        self.assertEqual(call["headers"]["Authorization"], "Bearer secret-token")

    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_skips_orders_with_old_created_and_old_delivery(self, mock_get, _mock_now):
        recent_created = _flowwow_order(id=11)
        future_delivery = _flowwow_order(
            id=12,
            createdDate=_ts(datetime(2026, 9, 17, 10, 0, tzinfo=_TB)),
            deliveryDateFrom=_ts(datetime(2026, 9, 20, 18, 0, tzinfo=_TB)),
            deliveryDateTo=_ts(datetime(2026, 9, 20, 18, 30, tzinfo=_TB)),
        )
        recent_delivery = _flowwow_order(
            id=13,
            createdDate=_ts(datetime(2026, 9, 17, 10, 0, tzinfo=_TB)),
            deliveryDateFrom=_ts(datetime(2026, 9, 19, 10, 0, tzinfo=_TB)),
            deliveryDateTo=_ts(datetime(2026, 9, 19, 10, 30, tzinfo=_TB)),
        )
        old = _flowwow_order(
            id=14,
            createdDate=_ts(datetime(2026, 9, 17, 10, 0, tzinfo=_TB)),
            deliveryDateFrom=_ts(datetime(2026, 9, 18, 10, 0, tzinfo=_TB)),
            deliveryDateTo=_ts(datetime(2026, 9, 18, 10, 30, tzinfo=_TB)),
        )
        self.items = [recent_created, future_delivery, recent_delivery, old]
        mock_get.side_effect = self._get
        from crm.flowwow import sync_flowwow_orders

        sync_flowwow_orders()
        self.assertEqual(
            set(CrmOrder.objects.values_list("flowwow_order_id", flat=True)),
            {11, 12, 13},
        )

    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_creates_crm_order_from_flowwow_payload(self, mock_get, _mock_now):
        self.items = [_flowwow_order()]
        mock_get.side_effect = self._get
        from crm.flowwow import sync_flowwow_orders

        sync_flowwow_orders()
        order = CrmOrder.objects.get(flowwow_order_id=25836184)
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
        self.assertEqual(order.internal_description, "напишите, пожалуйста, на тортике надпись")
        self.assertIn("Flowwow #25836184", order.description)
        self.assertIn("Filling: vanilla with strawberries", order.description)
        self.assertIn("Открытка: с днем рождения", order.description)
        self.assertIn("Покупатель: Саша 447472003498", order.description)
        self.assertIn("оставить у двери", order.description)
        self.assertIn("Курьеру: Orbi beach tower, комната 1720", order.description)
        images = list(order.images.order_by("position"))
        self.assertEqual([image.source_url for image in images], [_CAKE_IMAGE, _CARD_IMAGE])
        self.assertEqual(self.image_calls, [_CAKE_IMAGE, _CARD_IMAGE])

    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_uses_buyer_contact_when_recipient_missing(self, mock_get, _mock_now):
        self.items = [_flowwow_order(recipient=None)]
        mock_get.side_effect = self._get
        from crm.flowwow import sync_flowwow_orders

        sync_flowwow_orders()
        order = CrmOrder.objects.get(flowwow_order_id=25836184)
        self.assertEqual(order.contact, "Саша 447472003498")

    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_maps_pickup_and_asap_delivery(self, mock_get, _mock_now):
        self.items = [_flowwow_order(deliveryType=4, deliveryTimeType=1)]
        mock_get.side_effect = self._get
        from crm.flowwow import sync_flowwow_orders

        sync_flowwow_orders()
        order = CrmOrder.objects.get(flowwow_order_id=25836184)
        self.assertEqual(order.fulfillment_type, CrmOrder.FULFILLMENT_PICKUP)
        self.assertTrue(order.when_ready)
        self.assertIsNone(order.time_start)
        self.assertIsNone(order.time_end)

    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_repeated_sync_updates_without_duplicate_or_status_change(self, mock_get, _mock_now):
        first = _flowwow_order()
        second = _flowwow_order(
            address="улица Палиашвили, 16;",
            status=3,
            products=[
                {
                    "productId": 76014182,
                    "type": 1,
                    "name": "Бенто торт Горы",
                    "price": "60.00",
                    "count": 2,
                    "images": [_OTHER_IMAGE],
                    "selectedProperties": [
                        {
                            "propertyId": 45,
                            "propertyTitle": "Filling",
                            "valueId": 1148,
                            "valueTitle": "pistachio raspberry",
                        }
                    ],
                }
            ],
        )
        self.items = [first]
        mock_get.side_effect = self._get
        from crm.flowwow import sync_flowwow_orders

        sync_flowwow_orders()
        order = CrmOrder.objects.get(flowwow_order_id=25836184)
        order.status = CrmOrder.STATUS_IN_WORK
        order.save(update_fields=["status"])
        manual = CrmOrderImage.objects.create(
            order=order,
            image=_jpeg_file("manual.jpg"),
            position=10,
        )
        self.image_calls.clear()
        self.items = [second]
        sync_flowwow_orders()
        self.assertEqual(CrmOrder.objects.filter(flowwow_order_id=25836184).count(), 1)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_IN_WORK)
        self.assertEqual(order.delivery_address, "улица Палиашвили, 16;")
        self.assertEqual(order.cake_price, Decimal("120.00"))
        self.assertEqual(order.filling, "pistachio raspberry")
        urls = set(order.images.values_list("source_url", flat=True))
        self.assertEqual(urls, {_OTHER_IMAGE, None})
        self.assertTrue(CrmOrderImage.objects.filter(pk=manual.pk).exists())
        self.assertFalse(CrmOrderImage.objects.filter(source_url=_CAKE_IMAGE).exists())
        self.assertEqual(self.image_calls, [_OTHER_IMAGE])

    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_does_not_redownload_existing_images(self, mock_get, _mock_now):
        self.items = [_flowwow_order()]
        mock_get.side_effect = self._get
        from crm.flowwow import sync_flowwow_orders

        sync_flowwow_orders()
        self.image_calls.clear()
        sync_flowwow_orders()
        self.assertEqual(CrmOrderImage.objects.count(), 2)
        self.assertEqual(self.image_calls, [])


class FlowwowProductFieldsTests(TestCase):
    def test_uses_selected_weight_and_filling_properties(self):
        products = [
            {
                "type": 1,
                "name": "Cake 900 grams",
                "description": "",
                "selectedProperties": [
                    {
                        "propertyId": 10,
                        "propertyTitle": "Weight",
                        "valueTitle": "1.2 kg",
                    },
                    {
                        "propertyId": 45,
                        "propertyTitle": "Начинка",
                        "valueTitle": "mango passion fruit",
                    },
                ],
            }
        ]
        self.assertEqual(_weight(products), "1.2 kg")
        self.assertEqual(_filling(products), "mango passion fruit")

    def test_extracts_weight_from_description_when_name_has_no_weight(self):
        products = [
            {
                "type": 1,
                "name": "Бенто торт",
                "description": "Вес готового торта 0,9 кг",
                "selectedProperties": [],
            }
        ]
        self.assertEqual(_weight(products), "0,9 кг")
        self.assertEqual(_filling(products), "—")


class FlowwowSyncCommandTests(TestCase):
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_flowwow_orders")
    def test_existing_timer_command_imports_flowwow_orders(self, mock_sync):
        call_command("sync_crm_orders_to_telegram")
        mock_sync.assert_called_once_with()


def _ok_post_response() -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    return response


def _error_post_response(status_code: int) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    error = requests.HTTPError(response=response)
    response.raise_for_status.side_effect = error
    return response


def _flowwow_crm_order(**overrides) -> CrmOrder:
    fields = {
        "date": date(2026, 8, 25),
        "time_start": time(11, 0),
        "contact": "Customer",
        "fulfillment_type": CrmOrder.FULFILLMENT_DELIVERY,
        "weight": "2kg",
        "filling": "Mango",
        "cake_price": Decimal("100.00"),
        "prepayment": Decimal("100.00"),
        "status": CrmOrder.STATUS_CLIENT_APPROVED,
        "is_paid": True,
        "payment_type": CrmOrder.PAYMENT_FLOWWOW,
        "flowwow_order_id": 9977016,
    }
    fields.update(overrides)
    return CrmOrder.objects.create(**fields)


@override_settings(FLOWWOW_API_TOKEN=_TOKEN, FLOWWOW_SHOP_ID=_SHOP_ID)
class FlowwowCourierLeftSyncTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="worker", password="password")
        self.admin = User.objects.create_user(username="admin", password="password", is_staff=True)

    def _assert_post(self, mock_post, url: str, order_id: int):
        mock_post.assert_called_once()
        call = mock_post.call_args
        self.assertEqual(call.args[0], url)
        self.assertEqual(call.kwargs["json"], {"orderId": order_id})
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer secret-token")
        self.assertEqual(call.kwargs["headers"]["Accept"], "*/*")
        self.assertEqual(call.kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(call.kwargs["timeout"], 60)

    def _assert_courier_left(self, mock_post, order_id: int):
        self._assert_post(
            mock_post,
            "https://apis.flowwow.com/apiseller/orders/courierLeft",
            order_id,
        )

    def _assert_finish(self, mock_post, order_id: int):
        self._assert_post(
            mock_post,
            "https://apis.flowwow.com/apiseller/orders/finish",
            order_id,
        )

    @patch("crm.flowwow.requests.post", return_value=_ok_post_response())
    def test_patch_in_delivery_posts_courier_left(self, mock_post):
        order = _flowwow_crm_order()
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_IN_DELIVERY},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_IN_DELIVERY)
        self._assert_courier_left(mock_post, 9977016)

    @patch("crm.flowwow.requests.post")
    def test_patch_other_status_does_not_post(self, mock_post):
        order = _flowwow_crm_order()
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_READY},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_READY)
        mock_post.assert_not_called()

    @patch("crm.flowwow.requests.post")
    def test_patch_in_delivery_without_flowwow_id_does_not_post(self, mock_post):
        order = _flowwow_crm_order(flowwow_order_id=None)
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_IN_DELIVERY},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_IN_DELIVERY)
        mock_post.assert_not_called()

    @patch("crm.flowwow.requests.post")
    def test_put_already_in_delivery_does_not_post(self, mock_post):
        order = _flowwow_crm_order(status=CrmOrder.STATUS_IN_DELIVERY)
        self.client.force_authenticate(user=self.admin)
        payload = {
            "date": "2026-08-25",
            "time_start": "11:00:00",
            "contact": "Updated",
            "delivery_address": "Rustaveli 1",
            "fulfillment_type": CrmOrder.FULFILLMENT_DELIVERY,
            "status": CrmOrder.STATUS_IN_DELIVERY,
            "weight": "2kg",
            "filling": "Mango",
            "cake_price": "100.00",
            "prepayment": "100.00",
            "is_paid": True,
            "payment_type": CrmOrder.PAYMENT_FLOWWOW,
        }
        response = self.client.put(f"/api/crm/orders/{order.id}/", payload, format="multipart")
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_IN_DELIVERY)
        self.assertEqual(order.contact, "Updated")
        mock_post.assert_not_called()

    @patch("crm.flowwow.requests.post", return_value=_error_post_response(400))
    def test_http_400_does_not_retry_and_keeps_status(self, mock_post):
        order = _flowwow_crm_order()
        self.client.force_authenticate(user=self.user)
        with self.assertRaises(requests.HTTPError):
            self.client.patch(
                f"/api/crm/orders/{order.id}/",
                {"status": CrmOrder.STATUS_IN_DELIVERY},
                format="json",
            )
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_CLIENT_APPROVED)
        self.assertEqual(mock_post.call_count, 1)

    @patch("crm.flowwow.requests.post")
    def test_timeout_then_success_retries_and_saves(self, mock_post):
        mock_post.side_effect = [requests.Timeout(), _ok_post_response()]
        order = _flowwow_crm_order()
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_IN_DELIVERY},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_IN_DELIVERY)
        self.assertEqual(mock_post.call_count, 2)

    @patch("crm.flowwow.requests.post", side_effect=requests.Timeout())
    def test_three_timeouts_keep_status(self, mock_post):
        order = _flowwow_crm_order()
        self.client.force_authenticate(user=self.user)
        with self.assertRaises(requests.Timeout):
            self.client.patch(
                f"/api/crm/orders/{order.id}/",
                {"status": CrmOrder.STATUS_IN_DELIVERY},
                format="json",
            )
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_CLIENT_APPROVED)
        self.assertEqual(mock_post.call_count, 3)

    @patch("crm.flowwow.requests.post", return_value=_ok_post_response())
    def test_patch_delivered_posts_finish(self, mock_post):
        order = _flowwow_crm_order()
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_DELIVERED},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_DELIVERED)
        self._assert_finish(mock_post, 9977016)

    @patch("crm.flowwow.requests.post")
    def test_patch_delivered_without_flowwow_id_does_not_post(self, mock_post):
        order = _flowwow_crm_order(flowwow_order_id=None)
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_DELIVERED},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_DELIVERED)
        mock_post.assert_not_called()

    @patch("crm.flowwow.requests.post")
    def test_put_already_delivered_does_not_post(self, mock_post):
        order = _flowwow_crm_order(status=CrmOrder.STATUS_DELIVERED)
        self.client.force_authenticate(user=self.admin)
        payload = {
            "date": "2026-08-25",
            "time_start": "11:00:00",
            "contact": "Updated",
            "delivery_address": "Rustaveli 1",
            "fulfillment_type": CrmOrder.FULFILLMENT_DELIVERY,
            "status": CrmOrder.STATUS_DELIVERED,
            "weight": "2kg",
            "filling": "Mango",
            "cake_price": "100.00",
            "prepayment": "100.00",
            "is_paid": True,
            "payment_type": CrmOrder.PAYMENT_FLOWWOW,
        }
        response = self.client.put(f"/api/crm/orders/{order.id}/", payload, format="multipart")
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_DELIVERED)
        self.assertEqual(order.contact, "Updated")
        mock_post.assert_not_called()

    @patch("crm.flowwow.requests.post", return_value=_error_post_response(400))
    def test_finish_http_400_does_not_retry_and_keeps_status(self, mock_post):
        order = _flowwow_crm_order()
        self.client.force_authenticate(user=self.user)
        with self.assertRaises(requests.HTTPError):
            self.client.patch(
                f"/api/crm/orders/{order.id}/",
                {"status": CrmOrder.STATUS_DELIVERED},
                format="json",
            )
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_CLIENT_APPROVED)
        self.assertEqual(mock_post.call_count, 1)

    @patch("crm.flowwow.requests.post")
    def test_finish_timeout_then_success_retries_and_saves(self, mock_post):
        mock_post.side_effect = [requests.Timeout(), _ok_post_response()]
        order = _flowwow_crm_order()
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_DELIVERED},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_DELIVERED)
        self.assertEqual(mock_post.call_count, 2)

    @patch("crm.flowwow.requests.post", side_effect=requests.Timeout())
    def test_finish_three_timeouts_keep_status(self, mock_post):
        order = _flowwow_crm_order()
        self.client.force_authenticate(user=self.user)
        with self.assertRaises(requests.Timeout):
            self.client.patch(
                f"/api/crm/orders/{order.id}/",
                {"status": CrmOrder.STATUS_DELIVERED},
                format="json",
            )
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_CLIENT_APPROVED)
        self.assertEqual(mock_post.call_count, 3)
