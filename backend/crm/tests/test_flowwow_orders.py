import io
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

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
        self.items_by_date_page: dict[tuple[str, int], tuple[list[dict], int]] = {}

    def _get(self, url, params=None, headers=None, timeout=None):
        if url == "https://apis.flowwow.com/apiseller/orders/list":
            self.list_calls.append({"params": params, "headers": headers})
            key = (params["createdDate"], params["page"])
            items, total = self.items_by_date_page[key]
            return _list_response(items, total)
        self.image_calls.append(url)
        return _image_response()

    def _set_pages(self, mapping: dict[tuple[str, int], tuple[list[dict], int]]):
        self.items_by_date_page = mapping
        for created_date in ("2026-09-18", "2026-09-19"):
            if (created_date, 0) not in self.items_by_date_page:
                self.items_by_date_page[(created_date, 0)] = ([], 0)

    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_fetches_pages_with_bearer_and_limit(self, mock_get, _mock_now):
        page0 = _flowwow_order(id=1)
        page1 = _flowwow_order(id=2)
        self._set_pages(
            {
                ("2026-09-18", 0): ([page0], 2),
                ("2026-09-18", 1): ([page1], 2),
            }
        )
        mock_get.side_effect = self._get
        from crm.flowwow import sync_flowwow_orders

        sync_flowwow_orders()
        yesterday_pages = [
            call["params"]["page"]
            for call in self.list_calls
            if call["params"]["createdDate"] == "2026-09-18"
        ]
        self.assertEqual(yesterday_pages, [0, 1])
        for call in self.list_calls:
            self.assertEqual(call["params"]["shopId"], 395006)
            self.assertEqual(call["params"]["limit"], 100)
            self.assertEqual(call["headers"]["Authorization"], "Bearer secret-token")
            self.assertEqual(call["headers"]["Accept"], "*/*")
        self.assertEqual(
            set(CrmOrder.objects.values_list("flowwow_order_id", flat=True)),
            {1, 2},
        )

    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_skips_orders_older_than_24_hours(self, mock_get, _mock_now):
        recent = _flowwow_order(id=11)
        old = _flowwow_order(
            id=12,
            createdDate=_ts(datetime(2026, 9, 18, 14, 0, tzinfo=_TB)),
        )
        self._set_pages({("2026-09-18", 0): ([recent, old], 2)})
        mock_get.side_effect = self._get
        from crm.flowwow import sync_flowwow_orders

        sync_flowwow_orders()
        self.assertEqual(list(CrmOrder.objects.values_list("flowwow_order_id", flat=True)), [11])

    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_creates_crm_order_from_flowwow_payload(self, mock_get, _mock_now):
        self._set_pages({("2026-09-18", 0): ([_flowwow_order()], 1)})
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
        self.assertEqual(order.weight, "—")
        self.assertEqual(
            order.filling,
            "Бенто торт 900 грамм С ВАШЕЙ НАДПИСЬЮ, vanilla with strawberries",
        )
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
        self._set_pages({("2026-09-18", 0): ([_flowwow_order(recipient=None)], 1)})
        mock_get.side_effect = self._get
        from crm.flowwow import sync_flowwow_orders

        sync_flowwow_orders()
        order = CrmOrder.objects.get(flowwow_order_id=25836184)
        self.assertEqual(order.contact, "Саша 447472003498")

    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_maps_pickup_and_asap_delivery(self, mock_get, _mock_now):
        self._set_pages(
            {
                ("2026-09-18", 0): (
                    [_flowwow_order(deliveryType=4, deliveryTimeType=1)],
                    1,
                )
            }
        )
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
        self._set_pages({("2026-09-18", 0): ([first], 1)})
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
        self._set_pages({("2026-09-18", 0): ([second], 1)})
        sync_flowwow_orders()
        self.assertEqual(CrmOrder.objects.filter(flowwow_order_id=25836184).count(), 1)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_IN_WORK)
        self.assertEqual(order.delivery_address, "улица Палиашвили, 16;")
        self.assertEqual(order.cake_price, Decimal("120.00"))
        self.assertEqual(order.filling, "Бенто торт Горы, pistachio raspberry")
        urls = set(order.images.values_list("source_url", flat=True))
        self.assertEqual(urls, {_OTHER_IMAGE, None})
        self.assertTrue(CrmOrderImage.objects.filter(pk=manual.pk).exists())
        self.assertFalse(CrmOrderImage.objects.filter(source_url=_CAKE_IMAGE).exists())
        self.assertEqual(self.image_calls, [_OTHER_IMAGE])

    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_does_not_redownload_existing_images(self, mock_get, _mock_now):
        self._set_pages({("2026-09-18", 0): ([_flowwow_order()], 1)})
        mock_get.side_effect = self._get
        from crm.flowwow import sync_flowwow_orders

        sync_flowwow_orders()
        self.image_calls.clear()
        sync_flowwow_orders()
        self.assertEqual(CrmOrderImage.objects.count(), 2)
        self.assertEqual(self.image_calls, [])


class FlowwowSyncCommandTests(TestCase):
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_flowwow_orders")
    def test_existing_timer_command_imports_flowwow_orders(self, mock_sync):
        call_command("sync_crm_orders_to_telegram")
        mock_sync.assert_called_once_with()
