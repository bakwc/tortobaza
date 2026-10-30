import json
from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from cart.models import Cart, CartItem, CartItemOption
from catalog.models import Category, Option, OptionGroup, Product
from crm.models import CrmOrder, CrmOrderItem
from inventory.models import StockMovement
from menu.tests.fixtures import MenuFixture
from orders.models import Order
from orders.services import create_order_from_cart

_TB = ZoneInfo("Asia/Tbilisi")


def _frozen_now() -> datetime:
    return datetime(2026, 5, 21, 10, 0, tzinfo=_TB)


def _website_payload() -> dict:
    return {
        "locale": "en",
        "fulfillment_type": Order.FULFILLMENT_DELIVERY,
        "payment_method": Order.PAYMENT_CARD,
        "customer_name": "Anna",
        "customer_phone": "+995555111222",
        "customer_email": "anna@example.com",
        "customer_instagram": "",
        "customer_telegram": "",
        "comment": "",
        "schedule_mode": "slot",
        "schedule_date": _frozen_now().date(),
        "schedule_start_time": time(16, 0),
        "schedule_end_time": time(17, 0),
        "address": {
            "street": "Rustaveli",
            "building": "12",
            "apartment": "3",
            "city": "Batumi",
            "notes": "",
        },
    }


@patch("crm.website.schedule_crm_order_telegram_sync")
@patch("django.utils.timezone.now")
class WebsiteOrderItemsTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        category = Category.objects.create(
            name="Cakes",
            slug="cakes",
            position=0,
            delivery_schedule_tier=Product.DELIVERY_SCHEDULE_SAME_DAY,
        )
        self.product = Product.objects.create(
            category=category,
            name="Raspberry Dream",
            slug="raspberry-dream",
            description="",
            base_price=Decimal("100.00"),
            delivery_schedule_tier=Product.DELIVERY_SCHEDULE_SAME_DAY,
            tech_card=self.menu.cake,
        )
        weight_group = OptionGroup.objects.create(
            name="Weight",
            slug="weight",
            selection_type=OptionGroup.SELECTION_SINGLE,
        )
        self.weight_option = Option.objects.create(
            group=weight_group,
            name="2 kg",
            price_delta=Decimal("50.00"),
            position=0,
            weight_kg=Decimal("2.000"),
        )
        filling_group = OptionGroup.objects.create(
            name="Filling",
            slug="filling",
            selection_type=OptionGroup.SELECTION_SINGLE,
        )
        self.raspberry_option = Option.objects.create(
            group=filling_group,
            name="Raspberry",
            price_delta=Decimal("0.00"),
            position=0,
        )
        self.menu.raspberry_filling.catalog_option = self.raspberry_option
        self.menu.raspberry_filling.save()
        self.unmatched_option = Option.objects.create(
            group=filling_group,
            name="Pistachio",
            price_delta=Decimal("0.00"),
            position=1,
        )

    def _order(self, options: list[Option]) -> CrmOrder:
        cart = Cart.objects.create()
        item = CartItem.objects.create(cart=cart, product=self.product, quantity=1, comment="write name")
        for option in options:
            CartItemOption.objects.create(cart_item=item, option=option)
        order = create_order_from_cart(cart, _website_payload(), Order.ENV_PROD)
        return CrmOrder.objects.get(website_order=order)

    def test_items_are_transferred_from_website(self, mock_now, mock_sync):
        mock_now.return_value = _frozen_now()
        crm = self._order([self.weight_option, self.raspberry_option])
        item = crm.items.get()
        self.assertEqual(item.tech_card, self.menu.cake)
        self.assertEqual(item.weight_kg, Decimal("2.000"))
        self.assertEqual(item.name, "Raspberry Dream")
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.price, Decimal("150.00"))
        self.assertEqual(item.comment, "write name")
        self.assertFalse(item.needs_review)
        self.assertEqual(
            [(row.modifier, row.quantity) for row in item.modifiers.all()],
            [(self.menu.raspberry_filling, 1)],
        )

    def test_legacy_fields_are_unchanged(self, mock_now, mock_sync):
        mock_now.return_value = _frozen_now()
        crm = self._order([self.weight_option, self.raspberry_option])
        self.assertEqual(crm.filling, "Raspberry")
        self.assertEqual(crm.cake_price, crm.website_order.total - crm.website_order.delivery_fee)
        self.assertEqual(crm.delivery_price, crm.website_order.delivery_fee)
        self.assertEqual(crm.status, CrmOrder.STATUS_UNCONFIRMED)
        self.assertFalse(StockMovement.objects.exists())

    def test_unmatched_option_needs_review(self, mock_now, mock_sync):
        mock_now.return_value = _frozen_now()
        crm = self._order([self.weight_option, self.unmatched_option])
        item = crm.items.get()
        self.assertTrue(item.needs_review)
        self.assertEqual(item.tech_card, self.menu.cake)

    def test_product_without_tech_card_needs_review(self, mock_now, mock_sync):
        mock_now.return_value = _frozen_now()
        self.product.tech_card = None
        self.product.save()
        crm = self._order([self.weight_option, self.raspberry_option])
        item = crm.items.get()
        self.assertTrue(item.needs_review)
        self.assertIsNone(item.tech_card)
        self.assertFalse(item.modifiers.exists())

    def test_weighted_card_without_weight_option_needs_review(self, mock_now, mock_sync):
        mock_now.return_value = _frozen_now()
        crm = self._order([self.raspberry_option])
        item = crm.items.get()
        self.assertTrue(item.needs_review)
        self.assertIsNone(item.tech_card)
        self.assertIsNone(item.weight_kg)


class CrmOrderItemsApiTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        self.client = APIClient()
        self.admin = User.objects.create_user(username="admin", password="password", is_staff=True)
        self.finance = User.objects.create_user(username="finance", password="password", is_staff=True)
        UserProfile.objects.create(user=self.finance, is_finance_admin=True)
        self.menu.cake.sale_price = Decimal("60.00")
        self.menu.cake.save(update_fields=["sale_price"])
        self.order = CrmOrder.objects.create(
            date=date(2026, 10, 20),
            time_start=time(12, 0),
            contact="Customer",
            fulfillment_type=CrmOrder.FULFILLMENT_DELIVERY,
            weight="2kg",
            filling="Raspberry",
            cake_price=Decimal("120.00"),
            prepayment=Decimal("0.00"),
            payment_type=CrmOrder.PAYMENT_CASH,
        )

    def _payload(self, status: str, items: list[dict] | None) -> dict:
        payload = {
            "date": "2026-10-20",
            "time_start": "12:00:00",
            "contact": "Customer",
            "nickname": "",
            "delivery_address": "Rustaveli 1",
            "fulfillment_type": CrmOrder.FULFILLMENT_DELIVERY,
            "status": status,
            "weight": "2kg",
            "filling": "Raspberry",
            "description": "",
            "internal_description": "",
            "cake_price": "120.00",
            "prepayment": "0.00",
            "is_paid": False,
            "payment_type": CrmOrder.PAYMENT_CASH,
        }
        if items is not None:
            payload["items"] = json.dumps(items)
        return payload

    def _cake_item(self, weight_kg: str | None) -> dict:
        return {
            "tech_card": self.menu.cake.pk,
            "name": "",
            "quantity": 1,
            "weight_kg": weight_kg,
            "price": "120.00",
            "comment": "",
            "needs_review": False,
            "modifiers": [{"modifier": self.menu.raspberry_filling.pk, "quantity": 1}],
            "lines": [],
        }

    def _put(self, payload: dict):
        return self.client.put(f"/api/crm/orders/{self.order.pk}/", payload, format="multipart")

    def test_order_without_items_works_as_before(self):
        self.client.force_authenticate(self.admin)
        response = self._put(self._payload(CrmOrder.STATUS_READY, None))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["items"], [])
        self.assertFalse(StockMovement.objects.exists())

    def test_put_with_items_and_ready_status_writes_off(self):
        self.client.force_authenticate(self.admin)
        response = self._put(self._payload(CrmOrder.STATUS_READY, [self._cake_item("2")]))
        self.assertEqual(response.status_code, 200, response.content)
        item = CrmOrderItem.objects.get(order=self.order)
        self.assertEqual(item.weight_kg, Decimal("2.000"))
        self.assertEqual(item.modifiers.get().modifier, self.menu.raspberry_filling)
        movements = {
            movement.ingredient_id: movement.quantity
            for movement in StockMovement.objects.filter(crm_order=self.order)
        }
        self.assertEqual(
            movements,
            {
                self.menu.flour.pk: Decimal("-600"),
                self.menu.sugar.pk: Decimal("-400"),
                self.menu.cream.pk: Decimal("-600"),
                self.menu.raspberry.pk: Decimal("-200"),
            },
        )

    def test_put_without_items_keeps_existing_items(self):
        self.client.force_authenticate(self.admin)
        self._put(self._payload(CrmOrder.STATUS_NEW, [self._cake_item("2")]))
        response = self._put(self._payload(CrmOrder.STATUS_NEW, None))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(CrmOrderItem.objects.filter(order=self.order).count(), 1)

    def test_weighted_item_without_weight_is_rejected(self):
        self.client.force_authenticate(self.admin)
        response = self._put(self._payload(CrmOrder.STATUS_NEW, [self._cake_item(None)]))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CrmOrderItem.objects.exists())

    def test_item_price_scales_by_weight_and_quantity(self):
        self.client.force_authenticate(self.admin)
        item = self._cake_item("1.5")
        item["quantity"] = 2
        item["price"] = "1.00"
        payload = self._payload(CrmOrder.STATUS_NEW, [item])
        payload["cake_price"] = "999.00"
        response = self._put(payload)
        self.assertEqual(response.status_code, 200, response.content)
        saved = CrmOrderItem.objects.get(order=self.order)
        self.assertEqual(saved.price, Decimal("180.00"))
        self.order.refresh_from_db()
        self.assertEqual(self.order.cake_price, Decimal("999.00"))

    def test_piece_item_price_scales_by_quantity(self):
        self.menu.bento.basis_quantity = 2
        self.menu.bento.sale_price = Decimal("25.00")
        self.menu.bento.save(update_fields=["basis_quantity", "sale_price"])
        self.client.force_authenticate(self.admin)
        response = self._put(
            self._payload(
                CrmOrder.STATUS_NEW,
                [
                    {
                        "tech_card": self.menu.bento.pk,
                        "name": "",
                        "quantity": 4,
                        "weight_kg": None,
                        "price": "1.00",
                        "comment": "",
                        "needs_review": False,
                        "modifiers": [],
                        "lines": [],
                    }
                ],
            )
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(CrmOrderItem.objects.get(order=self.order).price, Decimal("50.00"))

    def test_item_without_sale_price_is_rejected(self):
        self.menu.cake.sale_price = None
        self.menu.cake.save(update_fields=["sale_price"])
        self.client.force_authenticate(self.admin)
        response = self._put(self._payload(CrmOrder.STATUS_NEW, [self._cake_item("2")]))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CrmOrderItem.objects.filter(order=self.order).exists())

    def test_food_cost_only_for_finance_admin(self):
        self.client.force_authenticate(self.admin)
        self._put(self._payload(CrmOrder.STATUS_NEW, [self._cake_item("2")]))
        self.assertNotIn("food_cost", self.client.get(f"/api/crm/orders/{self.order.pk}/").json())
        self.client.force_authenticate(self.finance)
        data = self.client.get(f"/api/crm/orders/{self.order.pk}/").json()
        self.assertEqual(data["food_cost"], "26.00")

    def test_order_item_cost_for_staff(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/crm/order-item-cost/",
            {
                "tech_card": self.menu.cake.pk,
                "quantity": 1,
                "weight_kg": "1",
                "modifiers": [],
                "lines": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["cost"], "10.00")

    def test_order_item_cost_includes_modifier_weight_and_extra_line(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/crm/order-item-cost/",
            {
                "tech_card": self.menu.cake.pk,
                "quantity": 1,
                "weight_kg": "2",
                "modifiers": [{"modifier": self.menu.raspberry_filling.pk, "quantity": 1}],
                "lines": [
                    {
                        "ingredient": self.menu.flour.pk,
                        "semi_product": None,
                        "quantity": "100",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["cost"], "27.00")

    def test_order_item_cost_without_required_modifier(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/crm/order-item-cost/",
            {
                "tech_card": self.menu.cake.pk,
                "quantity": 2,
                "weight_kg": "1",
                "modifiers": [],
                "lines": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["cost"], "20.00")

    def test_order_item_cost_forbidden_for_non_staff(self):
        user = User.objects.create_user(username="manager", password="password")
        self.client.force_authenticate(user)
        response = self.client.post(
            "/api/crm/order-item-cost/",
            {
                "tech_card": self.menu.cake.pk,
                "quantity": 1,
                "weight_kg": "1",
                "modifiers": [],
                "lines": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
