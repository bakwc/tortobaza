import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from catalog.models import Option, OptionGroup
from crm.analytics import products
from crm.analytics_composition import sync_analytics_composition
from crm.models import AnalyticsOrderComposition, AnalyticsOrderCompositionItem, CrmOrder
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

    def test_products_skip_orders_without_snapshot(self):
        _crm(date=date(2026, 10, 2), weight="1 кг", filling="Сникерс")
        first = _crm(date=date(2026, 10, 3), weight="1 кг", filling="snickers", cake_price=Decimal("40.00"))
        second = _crm(date=date(2026, 10, 4), weight="700", filling="Snickers", cake_price=Decimal("30.00"))
        addon = _crm(
            date=date(2026, 10, 5),
            weight="—",
            filling="—",
            description="Открытка × 2 — 0.00",
        )
        september = _crm(date=date(2026, 9, 1), weight="2 кг", filling="Сникерс")
        deleted = _crm(date=date(2026, 10, 6), weight="1 кг", filling="Сникерс", deleted=True)
        sync_analytics_composition(first)
        sync_analytics_composition(second)
        sync_analytics_composition(addon)
        sync_analytics_composition(september)
        sync_analytics_composition(deleted)
        report = products("2026-10", date(2026, 10, 25))
        self.assertEqual(report["coverage"], {"orders": 4, "parsed": 3})
        self.assertEqual(report["fillings"][0]["filling"], "Сникерс")
        self.assertEqual(report["fillings"][0]["quantity"], 2)
        self.assertEqual(report["fillings"][0]["orders"], 2)
        self.assertEqual(report["fillings"][0]["kilograms"], "1.7")
        self.assertEqual({row["kg"]: row["quantity"] for row in report["weights"]}, {"0.7": 1, "1": 1})
        self.assertEqual(report["weight_unknown"], 2)
        kinds = {row["kind"]: row["quantity"] for row in report["kinds"]}
        self.assertEqual(kinds["cake"], 2)
        self.assertEqual(kinds["addon"], 2)
        positions = {row["name"]: row for row in report["positions"]}
        self.assertEqual(positions["Торт"]["quantity"], 2)
        self.assertEqual(positions["Торт"]["orders"], 2)
        self.assertEqual(positions["Торт"]["kilograms"], "1.7")
        self.assertEqual(positions["Открытка"]["kind"], "addon")
        self.assertEqual(positions["Открытка"]["quantity"], 2)


class AnalyticsProductsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.worker = User.objects.create_user(username="worker", password="password")
        self.staff = User.objects.create_user(username="staff", password="password", is_staff=True)
        self.finance = User.objects.create_user(username="finance", password="password")
        UserProfile.objects.create(user=self.finance, is_finance_admin=True)

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
