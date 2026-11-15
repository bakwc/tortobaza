import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.permissions import grant
from catalog.models import Option, OptionGroup
from crm.analytics import products
from crm.analytics_composition import sync_analytics_composition
from crm.models import (
    AnalyticsOrderComposition,
    AnalyticsOrderCompositionItem,
    CrmOrder,
    CrmOrderItem,
    CrmOrderItemModifier,
)
from menu.models import TechCardCategory
from menu.tests.fixtures import MenuFixture
from orders.models import Order, OrderItem, OrderItemOption


def _crm(**kwargs) -> CrmOrder:
    fields = {
        "date": date(2026, 10, 10),
        "contact": "Customer",
        "weight": "1 кг",
        "filling": "Сникерс",
        "cake_price": Decimal("80.00"),
        "description": "",
    }
    fields.update(kwargs)
    return CrmOrder.objects.create(**fields)


def _website() -> Order:
    return Order.objects.create(
        fulfillment_type=Order.FULFILLMENT_PICKUP,
        payment_method=Order.PAYMENT_CASH,
        customer_name="Site",
        customer_phone="555000000",
        customer_email="site@example.com",
    )


class AnalyticsOrderCompositionTests(TestCase):
    def test_website_items_skip_llm(self):
        website = _website()
        item = OrderItem.objects.create(
            order=website,
            product_name="Капец ты дед",
            unit_price=Decimal("65.00"),
            quantity=2,
            line_total=Decimal("130.00"),
        )
        weight_group = OptionGroup.objects.create(name="Weight", slug="weight-analytics")
        weight_option = Option.objects.create(
            group=weight_group,
            name="600 gramm",
            price_delta=Decimal("0.00"),
            weight_kg=Decimal("0.600"),
        )
        filling_group = OptionGroup.objects.create(name="Filling", slug="filling-analytics")
        filling_option = Option.objects.create(
            group=filling_group,
            name="snickers",
            price_delta=Decimal("0.00"),
        )
        OrderItemOption.objects.create(
            order_item=item,
            option=weight_option,
            group_name="Weight",
            option_name="600 gramm",
            price_delta=Decimal("0.00"),
        )
        OrderItemOption.objects.create(
            order_item=item,
            option=filling_option,
            group_name="flovers bento",
            option_name="snickers",
            price_delta=Decimal("0.00"),
        )
        order = _crm(
            website_order=website,
            weight="—",
            filling="—",
            cake_price=Decimal("130.00"),
            description="Другой торт × 1 — 10.00\n  Filling: медовик",
        )
        with patch("crm.analytics_composition.OpenAI") as openai_cls:
            sync_analytics_composition(order)
            openai_cls.assert_not_called()
        row = AnalyticsOrderCompositionItem.objects.get()
        self.assertEqual(row.kind, AnalyticsOrderCompositionItem.KIND_CAKE)
        self.assertEqual(row.name, "Капец ты дед")
        self.assertEqual(row.quantity, 2)
        self.assertEqual(row.weight_kg, Decimal("0.600"))
        self.assertEqual(row.filling, "Сникерс")
        self.assertEqual(row.price, Decimal("130.00"))
        self.assertEqual(row.composition.parser, AnalyticsOrderComposition.PARSER_RULES)

    def test_flowwow_lines(self):
        description = "\n".join(
            [
                "Flowwow #26215650",
                "Бенто торт 700 грамм",
                "С ВАШИМ фото палороид × 1 — 75.00",
                "  Filling: mango passion fruit",
                "Бенто торт Лапка об Лапку × 1 — 65.00",
                "  Filling: морковь и груша",
                "Бенто торт 900 грамм С ВАШЕЙ НАДПИСЬЮ × 1 — 80.00",
                "  Filling: snickers",
                "Банкейк манго маракуйя × 1 — 15.00",
                "  flovers bento: mango passion fruit, Weight: 600 gramm",
                "Банкейк ореховое наслаждение × 1 — 15.00",
                "  Filling: ореховое наслаждение",
                "Открытка: с днем рождения",
                "Открытка × 1 — 0.00",
                "Съедобная фотопечать × 1 — 10.00",
                "Покупатель: 995593567293",
                "Курьеру: подъезд",
            ]
        )
        order = _crm(weight="—", filling="—", description=description)
        with patch("crm.analytics_composition.OpenAI") as openai_cls:
            sync_analytics_composition(order)
            openai_cls.assert_not_called()
        rows = list(AnalyticsOrderCompositionItem.objects.order_by("position"))
        self.assertEqual(
            [(row.kind, row.name, row.quantity, row.weight_kg, row.filling, row.price) for row in rows],
            [
                (
                    AnalyticsOrderCompositionItem.KIND_BENTO,
                    "Бенто",
                    1,
                    Decimal("0.700"),
                    "Манго маракуйя",
                    Decimal("75.00"),
                ),
                (
                    AnalyticsOrderCompositionItem.KIND_BENTO,
                    "Бенто торт Лапка об Лапку",
                    1,
                    None,
                    "Морковный с грушей",
                    Decimal("65.00"),
                ),
                (
                    AnalyticsOrderCompositionItem.KIND_BENTO,
                    "Бенто",
                    1,
                    Decimal("0.900"),
                    "Сникерс",
                    Decimal("80.00"),
                ),
                (
                    AnalyticsOrderCompositionItem.KIND_CAKE,
                    "Банкейк манго маракуйя",
                    1,
                    Decimal("0.600"),
                    "Манго маракуйя",
                    Decimal("15.00"),
                ),
                (
                    AnalyticsOrderCompositionItem.KIND_CAKE,
                    "Банкейк ореховое наслаждение",
                    1,
                    None,
                    "Ореховое наслаждение",
                    Decimal("15.00"),
                ),
                (
                    AnalyticsOrderCompositionItem.KIND_ADDON,
                    "Открытка",
                    1,
                    None,
                    "",
                    Decimal("0.00"),
                ),
                (
                    AnalyticsOrderCompositionItem.KIND_ADDON,
                    "Съедобная фотопечать",
                    1,
                    None,
                    "",
                    Decimal("10.00"),
                ),
            ],
        )
        self.assertEqual(rows[0].composition.parser, AnalyticsOrderComposition.PARSER_RULES)

    def test_simple_cake(self):
        order = _crm(weight="700", filling="snickers", description="Как на фото, но без надписи")
        with patch("crm.analytics_composition.OpenAI") as openai_cls:
            sync_analytics_composition(order)
            openai_cls.assert_not_called()
        row = AnalyticsOrderCompositionItem.objects.get()
        self.assertEqual(row.kind, AnalyticsOrderCompositionItem.KIND_CAKE)
        self.assertEqual(row.name, "Торт")
        self.assertEqual(row.quantity, 1)
        self.assertEqual(row.weight_kg, Decimal("0.700"))
        self.assertEqual(row.filling, "Сникерс")
        self.assertEqual(row.price, Decimal("80.00"))
        self.assertEqual(row.composition.parser, AnalyticsOrderComposition.PARSER_RULES)

    def test_llm_is_cached_until_description_changes(self):
        order = _crm(
            weight="1 кг",
            filling="фисташка малина 2 шт, сникерс 2 шт",
            description="набор",
        )
        payload = {
            "items": [
                {
                    "kind": "cake",
                    "name": "Торт",
                    "quantity": 2,
                    "weight_kg": 0.5,
                    "filling": "фисташка малина",
                    "price": None,
                },
                {
                    "kind": "cake",
                    "name": "Торт",
                    "quantity": 2,
                    "weight_kg": 0.5,
                    "filling": "snickers",
                    "price": "20.00",
                },
            ]
        }
        fake = SimpleNamespace(output_text=json.dumps(payload))
        with patch("crm.analytics_composition.OpenAI") as openai_cls:
            openai_cls.return_value.responses.create.return_value = fake
            sync_analytics_composition(order)
            sync_analytics_composition(order)
            self.assertEqual(openai_cls.return_value.responses.create.call_count, 1)
            order.description = "набор другой"
            order.save(update_fields=["description"])
            sync_analytics_composition(order)
            self.assertEqual(openai_cls.return_value.responses.create.call_count, 2)
        rows = list(AnalyticsOrderCompositionItem.objects.order_by("position"))
        self.assertEqual(rows[0].filling, "Фисташка малина")
        self.assertEqual(rows[0].quantity, 2)
        self.assertIsNone(rows[0].price)
        self.assertEqual(rows[1].filling, "Сникерс")
        self.assertEqual(rows[1].price, Decimal("20.00"))
        self.assertEqual(rows[0].composition.parser, AnalyticsOrderComposition.PARSER_LLM)

    def test_products_count_order_items(self):
        menu = MenuFixture()
        menu.filling.position = 0
        menu.filling.save(update_fields=["position"])
        menu.decor.position = 1
        menu.decor.save(update_fields=["position"])
        menu.cake.category = TechCardCategory.objects.create(name="Торты")
        menu.cake.save(update_fields=["category"])
        menu.bento.category = TechCardCategory.objects.create(name="Картошка")
        menu.bento.save(update_fields=["category"])
        _crm(date=date(2026, 10, 2), weight="1 кг", filling="Сникерс")
        first = _crm(date=date(2026, 10, 3), weight="1 кг", filling="snickers")
        second = _crm(date=date(2026, 10, 4), weight="700", filling="Snickers")
        pieces = _crm(date=date(2026, 10, 5), weight="—", filling="—")
        missing_weight = _crm(date=date(2026, 10, 6), weight="1 кг", filling="Сникерс")
        september = _crm(date=date(2026, 9, 1), weight="2 кг", filling="Сникерс")
        deleted = _crm(date=date(2026, 10, 7), weight="1 кг", filling="Сникерс", deleted=True)
        first_item = CrmOrderItem.objects.create(
            order=first,
            tech_card=menu.cake,
            quantity=1,
            weight_kg=Decimal("1"),
        )
        CrmOrderItemModifier.objects.create(item=first_item, modifier=menu.raspberry_filling, quantity=1)
        CrmOrderItemModifier.objects.create(item=first_item, modifier=menu.photo, quantity=2)
        second_item = CrmOrderItem.objects.create(
            order=second,
            tech_card=menu.cake,
            quantity=1,
            weight_kg=Decimal("0.7"),
        )
        CrmOrderItemModifier.objects.create(item=second_item, modifier=menu.raspberry_filling, quantity=1)
        CrmOrderItem.objects.create(order=pieces, tech_card=menu.bento, quantity=2)
        CrmOrderItem.objects.create(order=pieces, name="Открытка", quantity=2)
        CrmOrderItem.objects.create(order=missing_weight, tech_card=menu.cake, quantity=3)
        CrmOrderItem.objects.create(
            order=september,
            tech_card=menu.cake,
            quantity=1,
            weight_kg=Decimal("2"),
        )
        CrmOrderItem.objects.create(
            order=deleted,
            tech_card=menu.cake,
            quantity=1,
            weight_kg=Decimal("1"),
        )
        report = products("2026-10", date(2026, 10, 25))
        self.assertEqual(report["coverage"], {"orders": 5, "with_items": 4})
        cards = {row["name"]: row for row in report["tech_cards"]}
        self.assertEqual(cards["Cake"]["category"], "Торты")
        self.assertEqual(cards["Cake"]["quantity"], 5)
        self.assertEqual(cards["Cake"]["share"], "0.556")
        self.assertEqual(cards["Cake"]["orders"], 3)
        self.assertEqual(cards["Cake"]["kilograms"], "1.7")
        self.assertEqual(cards["Bento"]["category"], "Картошка")
        self.assertEqual(cards["Bento"]["quantity"], 2)
        self.assertEqual(cards["Bento"]["share"], "0.222")
        self.assertEqual(cards["Bento"]["kilograms"], "0")
        self.assertEqual(cards["Открытка"]["category"], "no_tech_card")
        self.assertEqual(cards["Открытка"]["quantity"], 2)
        self.assertEqual(cards["Открытка"]["share"], "0.222")
        categories = {row["name"]: row for row in report["categories"]}
        self.assertEqual(categories["Торты"]["quantity"], 5)
        self.assertEqual(categories["Торты"]["orders"], 3)
        self.assertEqual(categories["Торты"]["kilograms"], "1.7")
        self.assertEqual(categories["Картошка"]["quantity"], 2)
        self.assertEqual(categories["no_tech_card"]["quantity"], 2)
        self.assertEqual({row["kg"]: row["quantity"] for row in report["weights"]}, {"0.7": 1, "1": 1})
        self.assertEqual(report["weight_unknown"], 3)
        groups = {group["name"]: group for group in report["modifier_groups"]}
        self.assertEqual(list(groups), ["Filling", "Decor"])
        self.assertFalse(groups["Filling"]["multi"])
        self.assertEqual(groups["Filling"]["available"], 3)
        self.assertEqual(groups["Filling"]["selected"], 2)
        self.assertIsNone(groups["Filling"]["average"])
        self.assertEqual(groups["Filling"]["modifiers"][0]["name"], "Raspberry")
        self.assertEqual(groups["Filling"]["modifiers"][0]["quantity"], 2)
        self.assertEqual(groups["Filling"]["modifiers"][0]["orders"], 2)
        self.assertEqual(groups["Filling"]["modifiers"][0]["kilograms"], "1.7")
        self.assertTrue(groups["Decor"]["multi"])
        self.assertEqual(groups["Decor"]["available"], 3)
        self.assertEqual(groups["Decor"]["selected"], 1)
        self.assertEqual(groups["Decor"]["average"], "2")
        self.assertEqual(groups["Decor"]["modifiers"][0]["name"], "Photo print")
        self.assertEqual(groups["Decor"]["modifiers"][0]["quantity"], 2)
        self.assertEqual(groups["Decor"]["modifiers"][0]["kilograms"], "2")
        self.assertEqual(report["cross_sales"]["orders"], 4)
        self.assertEqual(report["cross_sales"]["multi_category"], 1)
        self.assertEqual(
            report["cross_sales"]["pairs"],
            [{"first": "no_tech_card", "second": "Картошка", "orders": 1}],
        )


class AnalyticsProductsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.worker = User.objects.create_user(username="worker", password="password")
        self.staff = User.objects.create_user(username="staff", password="password", is_staff=True)
        self.finance = User.objects.create_user(username="finance", password="password")
        grant(self.finance, "view_analytics")

    def test_unauthenticated_access_denied(self):
        response = self.client.get("/api/crm/analytics/products/")
        self.assertEqual(response.status_code, 403)

    def test_worker_access_denied(self):
        self.client.force_authenticate(user=self.worker)
        response = self.client.get("/api/crm/analytics/products/")
        self.assertEqual(response.status_code, 403)

    def test_staff_access_denied(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/api/crm/analytics/products/")
        self.assertEqual(response.status_code, 403)

    def test_finance_admin_can_read(self):
        self.client.force_authenticate(user=self.finance)
        response = self.client.get("/api/crm/analytics/products/")
        self.assertEqual(response.status_code, 200)
