from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.forms.models import model_to_dict
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.permissions import ORDER_STATUS_CODES, grant
from crm.admin import CrmOrderAdminForm
from crm.flowwow import _sync_items, sync_flowwow_orders
from crm.models import (
    CrmOrder,
    CrmOrderEvent,
    CrmOrderItem,
    FlowwowFilling,
    FlowwowProduct,
    FlowwowSubcategoryTechCard,
)
from crm.tests.test_flowwow_orders import _NOW, _TOKEN, _SHOP_ID, _flowwow_order, _image_response, _list_response
from menu.models import TechCardModifierGroup
from menu.tests.fixtures import MenuFixture


def _line(
    product_id: int,
    name: str,
    filling: str | None,
    type_: int = 1,
    price: str = "80.00",
    count: int = 1,
) -> dict:
    properties = []
    if filling is not None:
        properties = [
            {
                "propertyId": 45,
                "propertyTitle": "Filling",
                "valueId": 1,
                "valueTitle": filling,
            }
        ]
    return {
        "productId": product_id,
        "type": type_,
        "name": name,
        "price": price,
        "count": count,
        "selectedProperties": properties,
        "images": [],
    }


def _order() -> CrmOrder:
    return CrmOrder.objects.create(
        date=date(2026, 9, 19),
        contact="Anna",
        cake_price=Decimal("80.00"),
        status=CrmOrder.STATUS_UNCONFIRMED,
        payment_type=CrmOrder.PAYMENT_FLOWWOW,
        flowwow_order_id=1,
    )


def _catalog_product(product_id: int, volume_grams: int | None, sub_category_id: int = 385) -> FlowwowProduct:
    return FlowwowProduct.objects.create(
        product_id=product_id,
        offer_id="",
        name=f"Product {product_id}",
        type=1,
        category_id=5,
        sub_category_id=sub_category_id,
        volume_grams=volume_grams,
        fillings=[],
        is_active=True,
        is_archived=False,
        synced_at=timezone.now(),
    )


class FlowwowOrderItemTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        filling = FlowwowFilling.objects.create(title="snickers")
        filling.modifiers.add(self.menu.raspberry_filling)
        FlowwowSubcategoryTechCard.objects.create(
            sub_category_id=385,
            volume_grams=1000,
            tech_card=self.menu.cake,
        )

    def test_subcategory_rule_sets_tech_card_weight_and_filling(self):
        _catalog_product(10, 1000)
        order = _order()
        _sync_items(order, {"products": [_line(10, "Bento 1000", "Snickers")]})
        item = order.items.get()
        self.assertEqual(item.tech_card, self.menu.cake)
        self.assertEqual(item.weight_kg, Decimal("1.000"))
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.price, Decimal("80.00"))
        self.assertEqual(item.modifiers.get().modifier, self.menu.raspberry_filling)
        self.assertFalse(item.needs_review)

    def test_product_tech_card_overrides_subcategory_rule(self):
        TechCardModifierGroup.objects.create(tech_card=self.menu.bento, group=self.menu.filling)
        product = _catalog_product(10, 1000)
        product.tech_card = self.menu.bento
        product.save(update_fields=["tech_card"])
        order = _order()
        _sync_items(order, {"products": [_line(10, "Bento", "snickers")]})
        item = order.items.get()
        self.assertEqual(item.tech_card, self.menu.bento)
        self.assertIsNone(item.weight_kg)
        self.assertFalse(item.needs_review)

    def test_photo_print_is_a_modifier_and_postcard_is_skipped(self):
        _catalog_product(10, 1000)
        photo = _catalog_product(20, None)
        photo.type = 3
        photo.save(update_fields=["type"])
        photo.modifiers.add(self.menu.photo)
        order = _order()
        _sync_items(
            order,
            {
                "products": [
                    _line(10, "Bento", "snickers"),
                    _line(20, "Съедобная фотопечать", None, type_=3, price="10.00"),
                    _line(21, "Открытка", None, type_=3, price="0.00"),
                ]
            },
        )
        item = order.items.get()
        self.assertEqual(
            set(item.modifiers.values_list("modifier_id", flat=True)),
            {self.menu.raspberry_filling.pk, self.menu.photo.pk},
        )
        self.assertFalse(item.needs_review)

    def test_unknown_product_reloads_catalog(self):
        order = _order()

        def create_product():
            _catalog_product(99, 1000)

        with patch("crm.flowwow.sync_flowwow_catalog", side_effect=create_product) as mock_sync:
            _sync_items(order, {"products": [_line(99, "Bento", "snickers")]})
        mock_sync.assert_called_once()
        item = order.items.get()
        self.assertEqual(item.tech_card, self.menu.cake)
        self.assertFalse(item.needs_review)

    def test_product_missing_after_reload_needs_review(self):
        order = _order()
        with patch("crm.flowwow.sync_flowwow_catalog") as mock_sync:
            _sync_items(order, {"products": [_line(99, "Bento", "snickers")]})
        mock_sync.assert_called_once()
        item = order.items.get()
        self.assertIsNone(item.tech_card)
        self.assertTrue(item.needs_review)
        self.assertEqual(item.modifiers.count(), 0)

    def test_missing_filling_needs_review(self):
        _catalog_product(10, 1000)
        order = _order()
        _sync_items(order, {"products": [_line(10, "Bento", None)]})
        item = order.items.get()
        self.assertEqual(item.tech_card, self.menu.cake)
        self.assertTrue(item.needs_review)
        self.assertFalse(FlowwowFilling.objects.exclude(title="snickers").exists())

    def test_unmapped_filling_needs_review_and_is_stored(self):
        _catalog_product(10, 1000)
        order = _order()
        _sync_items(order, {"products": [_line(10, "Bento", "Mango")]})
        item = order.items.get()
        self.assertTrue(item.needs_review)
        self.assertTrue(FlowwowFilling.objects.filter(title="mango", modifiers=None).exists())

    def test_modifier_outside_tech_card_needs_review(self):
        filling = FlowwowFilling.objects.get(title="snickers")
        filling.modifiers.add(self.menu.balloon)
        _catalog_product(10, 1000)
        order = _order()
        _sync_items(order, {"products": [_line(10, "Bento", "snickers")]})
        self.assertTrue(order.items.get().needs_review)

    def test_missing_rule_needs_review(self):
        _catalog_product(10, 600)
        order = _order()
        _sync_items(order, {"products": [_line(10, "Bento", "snickers")]})
        item = order.items.get()
        self.assertIsNone(item.tech_card)
        self.assertTrue(item.needs_review)


@override_settings(FLOWWOW_API_TOKEN=_TOKEN, FLOWWOW_SHOP_ID=_SHOP_ID)
class FlowwowItemFailureTests(TestCase):
    @patch("crm.flowwow.timezone.now", return_value=_NOW)
    @patch("crm.flowwow.requests.get")
    def test_item_failure_still_creates_order(self, mock_get, _mock_now):
        item = _flowwow_order()
        mock_get.side_effect = lambda url, params=None, headers=None, timeout=None: (
            _list_response([item])
            if url == "https://apis.flowwow.com/apiseller/orders/list"
            else _image_response()
        )
        with patch("crm.flowwow.sync_flowwow_catalog", side_effect=RuntimeError("boom")):
            with self.assertLogs("crm.flowwow", level="ERROR") as logs:
                sync_flowwow_orders()
        order = CrmOrder.objects.get(flowwow_order_id=item["id"])
        self.assertEqual(order.contact, "kristina 595032371")
        self.assertEqual(order.items.count(), 0)
        self.assertEqual(order.images.count(), 2)
        self.assertTrue(
            CrmOrderEvent.objects.filter(
                order=order,
                action=CrmOrderEvent.ACTION_CREATED,
                source=CrmOrderEvent.SOURCE_FLOWWOW,
            ).exists()
        )
        self.assertTrue(any("flowwow items failed" in line for line in logs.output))


class FlowwowConfirmationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="worker", password="password")
        grant(self.user, "edit_orders", "view_orders", *ORDER_STATUS_CODES)
        self.client.force_authenticate(user=self.user)

    def _order(self) -> CrmOrder:
        return CrmOrder.objects.create(
            date=date(2026, 8, 25),
            contact="Customer",
            cake_price=Decimal("100.00"),
            status=CrmOrder.STATUS_UNCONFIRMED,
            payment_type=CrmOrder.PAYMENT_CASH,
        )

    def test_patch_without_items_is_rejected(self):
        order = self._order()
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_NEW},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_UNCONFIRMED)

    def test_patch_with_review_item_is_rejected(self):
        order = self._order()
        CrmOrderItem.objects.create(order=order, name="Cake", needs_review=True)
        response = self.client.patch(
            f"/api/crm/orders/{order.id}/",
            {"status": CrmOrder.STATUS_NEW},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_UNCONFIRMED)

    def test_put_with_review_items_is_rejected(self):
        order = self._order()
        CrmOrderItem.objects.create(order=order, name="Cake")
        response = self.client.put(
            f"/api/crm/orders/{order.id}/",
            {
                "date": "2026-08-25",
                "contact": "Customer",
                "fulfillment_type": CrmOrder.FULFILLMENT_DELIVERY,
                "status": CrmOrder.STATUS_NEW,
                "weight": "",
                "filling": "",
                "description": "",
                "internal_description": "",
                "cake_price": "100.00",
                "delivery_price": "0",
                "prepayment": "0",
                "is_paid": False,
                "payment_type": CrmOrder.PAYMENT_CASH,
                "items": '[{"tech_card": null, "name": "Cake", "quantity": 1, "weight_kg": null, "price": null, "comment": "", "needs_review": true, "modifiers": [], "lines": []}]',
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, CrmOrder.STATUS_UNCONFIRMED)
        self.assertFalse(order.items.get().needs_review)

    def test_admin_form_rejects_confirmation_without_items(self):
        order = self._order()
        data = model_to_dict(order)
        data["status"] = CrmOrder.STATUS_NEW
        form = CrmOrderAdminForm(data=data, instance=order)
        self.assertFalse(form.is_valid())
        self.assertIn("Set order items", form.errors["__all__"][0])
        CrmOrderItem.objects.create(order=order, name="Cake")
        form = CrmOrderAdminForm(data=data, instance=order)
        self.assertNotIn("__all__", form.errors)
