from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from crm.flowwow_catalog import sync_flowwow_catalog, sync_flowwow_catalog_if_stale
from crm.models import FinancialAccount, FlowwowProduct
from menu.tests.fixtures import MenuFixture

_TOKEN = "secret-token"
_SHOP_ID = "395006"


def _response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status = MagicMock()
    return response


def _product(product_id: int, volume: dict | None, filling: list[str] | None) -> dict:
    properties = None
    if volume is not None or filling is not None:
        properties = {}
        if volume is not None:
            properties["volume"] = volume
        if filling is not None:
            properties["filling"] = filling
    return {
        "offerId": "",
        "productId": product_id,
        "isActive": True,
        "isArchived": False,
        "type": 1,
        "categoryId": 5,
        "subCategoryId": 385,
        "name": f"Bento {product_id}",
        "description": "",
        "url": "https://flowwow.com/bento",
        "available": 1,
        "stock": 0,
        "minOrder": 1,
        "price": "80.00",
        "discount": "0",
        "currencyCode": "GEL",
        "images": [],
        "productionTime": 300,
        "shipmentTime": 0,
        "canRent": 0,
        "originalId": 0,
        "isDeliveryPost": False,
        "isStarred": False,
        "vat": "0",
        "stats": None,
        "properties": properties,
    }


def _stored_product(product_id: int, synced_at) -> FlowwowProduct:
    return FlowwowProduct.objects.create(
        product_id=product_id,
        offer_id="",
        name=f"Bento {product_id}",
        type=1,
        category_id=5,
        sub_category_id=385,
        volume_grams=700,
        fillings=[],
        is_active=True,
        is_archived=False,
        synced_at=synced_at,
    )


@override_settings(FLOWWOW_API_TOKEN=_TOKEN, FLOWWOW_SHOP_ID=_SHOP_ID)
class FlowwowCatalogSyncTests(TestCase):
    @patch("crm.flowwow_catalog.requests.post")
    def test_pages_volume_and_keeps_admin_fields(self, mock_post):
        menu = MenuFixture()
        mock_post.side_effect = [
            _response({"total": 2, "items": [_product(1, {"val": 1000, "measure": 2}, ["сникерс"])]}),
            _response({"total": 2, "items": [_product(2, {"val": 5, "measure": 5}, None)]}),
        ]
        with self.assertLogs("crm.flowwow_catalog", level="ERROR") as logs:
            sync_flowwow_catalog()
        self.assertEqual(FlowwowProduct.objects.count(), 2)
        first = FlowwowProduct.objects.get(product_id=1)
        self.assertEqual(first.volume_grams, 1000)
        self.assertEqual(first.fillings, ["сникерс"])
        self.assertIsNone(FlowwowProduct.objects.get(product_id=2).volume_grams)
        self.assertIn("product_id=2", logs.output[0])
        self.assertIn("measure=5", logs.output[0])
        self.assertEqual(mock_post.call_args_list[0].kwargs["params"], {"shopId": 395006})
        self.assertEqual(
            mock_post.call_args_list[0].kwargs["json"],
            {"extended": True, "limit": 1000, "page": 0},
        )
        self.assertEqual(mock_post.call_args_list[1].kwargs["json"]["page"], 1)
        first.tech_card = menu.cake
        first.modifiers.add(menu.photo)
        first.save(update_fields=["tech_card"])
        mock_post.side_effect = [
            _response({"total": 1, "items": [_product(1, {"val": 700, "measure": 2}, ["сникерс"])]}),
        ]
        sync_flowwow_catalog()
        first.refresh_from_db()
        self.assertEqual(first.volume_grams, 700)
        self.assertEqual(first.tech_card, menu.cake)
        self.assertEqual(list(first.modifiers.all()), [menu.photo])

    @patch("crm.flowwow_catalog.requests.post")
    def test_fresh_catalog_is_not_synced(self, mock_post):
        _stored_product(1, timezone.now())
        sync_flowwow_catalog_if_stale()
        mock_post.assert_not_called()

    @patch("crm.flowwow_catalog.requests.post")
    def test_stale_catalog_is_synced(self, mock_post):
        _stored_product(1, timezone.now() - timedelta(hours=25))
        mock_post.return_value = _response({"total": 0, "items": []})
        sync_flowwow_catalog_if_stale()
        mock_post.assert_called_once()

    @patch("crm.flowwow_catalog.requests.post")
    def test_empty_catalog_is_synced(self, mock_post):
        mock_post.return_value = _response({"total": 0, "items": []})
        sync_flowwow_catalog_if_stale()
        mock_post.assert_called_once()
        self.assertEqual(FlowwowProduct.objects.count(), 0)


class FlowwowCatalogCommandTests(TestCase):
    @patch("crm.management.commands.sync_crm_orders_to_telegram.import_card_sms", lambda: None)
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_invoices", lambda: None)
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_waybills", lambda: None)
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_flowwow_orders")
    @patch("crm.flowwow_catalog.sync_flowwow_catalog", side_effect=RuntimeError("boom"))
    def test_catalog_failure_still_syncs_orders(self, _mock_catalog, mock_orders):
        FinancialAccount.objects.create(name="PayPal", kind=FinancialAccount.KIND_BANK, currency="USD")
        with self.assertLogs(
            "crm.management.commands.sync_crm_orders_to_telegram",
            level="ERROR",
        ) as logs:
            call_command("sync_crm_orders_to_telegram")
        mock_orders.assert_called_once_with()
        self.assertTrue(any("flowwow catalog sync failed" in line for line in logs.output))
