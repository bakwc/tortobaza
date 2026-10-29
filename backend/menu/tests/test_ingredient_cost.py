from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from menu.models import IngredientCategory, TechCardCategory
from menu.tests.fixtures import MenuFixture


class IngredientCostApiTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        self.client = APIClient()
        self.staff = User.objects.create_user("chef", password="x")
        self.admin = User.objects.create_user("boss", password="x")
        UserProfile.objects.create(user=self.admin, is_finance_admin=True)
        self.flour = self.menu.flour

    def _payload(self, avg_cost: str | None) -> dict:
        payload = {"name": "Flour", "category": None, "unit": "g", "is_active": True}
        if avg_cost is not None:
            payload["avg_cost"] = avg_cost
        return payload

    def test_finance_admin_sets_average_cost(self):
        self.client.force_authenticate(self.admin)
        response = self.client.put(
            f"/api/menu/ingredients/{self.flour.pk}/",
            self._payload("0.004"),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.flour.refresh_from_db()
        self.assertEqual(self.flour.avg_cost, Decimal("0.004000"))
        self.assertEqual(Decimal(response.json()["avg_cost"]), Decimal("0.004"))

    def test_staff_update_keeps_average_cost(self):
        self.client.force_authenticate(self.staff)
        response = self.client.put(
            f"/api/menu/ingredients/{self.flour.pk}/",
            self._payload(None),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotIn("avg_cost", response.json())
        self.flour.refresh_from_db()
        self.assertEqual(self.flour.avg_cost, Decimal("0.01"))

    def test_staff_cannot_set_average_cost(self):
        self.client.force_authenticate(self.staff)
        response = self.client.put(
            f"/api/menu/ingredients/{self.flour.pk}/",
            self._payload("0.004"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.flour.refresh_from_db()
        self.assertEqual(self.flour.avg_cost, Decimal("0.01"))

    def test_finance_admin_sets_cost_quantity(self):
        self.client.force_authenticate(self.admin)
        payload = self._payload("0.004")
        payload["cost_quantity"] = "1000"
        response = self.client.put(
            f"/api/menu/ingredients/{self.flour.pk}/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.flour.refresh_from_db()
        self.assertEqual(self.flour.cost_quantity, Decimal("1000.000"))
        self.assertEqual(Decimal(response.json()["cost_quantity"]), Decimal("1000"))

    def test_staff_update_keeps_cost_quantity(self):
        self.flour.cost_quantity = Decimal("1000")
        self.flour.save(update_fields=["cost_quantity"])
        self.client.force_authenticate(self.staff)
        response = self.client.put(
            f"/api/menu/ingredients/{self.flour.pk}/",
            self._payload(None),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Decimal(response.json()["cost_quantity"]), Decimal("1000"))
        self.flour.refresh_from_db()
        self.assertEqual(self.flour.cost_quantity, Decimal("1000"))
        self.assertEqual(self.flour.avg_cost, Decimal("0.01"))

    def test_grams_clear_grams_per_unit(self):
        self.flour.grams_per_unit = Decimal("1")
        self.flour.save(update_fields=["grams_per_unit"])
        self.client.force_authenticate(self.admin)
        response = self.client.put(
            f"/api/menu/ingredients/{self.flour.pk}/",
            self._payload(None),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(response.json()["grams_per_unit"])
        self.flour.refresh_from_db()
        self.assertIsNone(self.flour.grams_per_unit)

    def test_milliliters_require_grams_per_unit(self):
        self.client.force_authenticate(self.admin)
        payload = self._payload(None)
        payload["name"] = "Oil"
        payload["unit"] = "ml"
        response = self.client.post("/api/menu/ingredients/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_milliliters_save_grams_per_unit(self):
        self.client.force_authenticate(self.admin)
        payload = self._payload(None)
        payload["name"] = "Oil"
        payload["unit"] = "ml"
        payload["grams_per_unit"] = "0.920"
        response = self.client.post("/api/menu/ingredients/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Decimal(response.json()["grams_per_unit"]), Decimal("0.920"))

    def test_staff_sets_and_clears_sale_price(self):
        self.client.force_authenticate(self.staff)
        payload = self._payload(None)
        payload["sale_price"] = "8.50"
        response = self.client.put(
            f"/api/menu/ingredients/{self.flour.pk}/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotIn("avg_cost", response.json())
        self.assertEqual(Decimal(response.json()["sale_price"]), Decimal("8.50"))
        self.flour.refresh_from_db()
        self.assertEqual(self.flour.sale_price, Decimal("8.50"))
        self.assertEqual(self.flour.avg_cost, Decimal("0.01"))

        payload["sale_price"] = None
        response = self.client.put(
            f"/api/menu/ingredients/{self.flour.pk}/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(response.json()["sale_price"])
        self.assertNotIn("avg_cost", response.json())
        self.flour.refresh_from_db()
        self.assertIsNone(self.flour.sale_price)

    def test_put_without_sale_price_keeps_it(self):
        self.flour.sale_price = Decimal("8.50")
        self.flour.save(update_fields=["sale_price"])
        self.client.force_authenticate(self.staff)
        response = self.client.put(
            f"/api/menu/ingredients/{self.flour.pk}/",
            self._payload(None),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Decimal(response.json()["sale_price"]), Decimal("8.50"))
        self.flour.refresh_from_db()
        self.assertEqual(self.flour.sale_price, Decimal("8.50"))

    def _bento_payload(self) -> dict:
        return {
            "name": "Bento",
            "category": None,
            "kind": "piece",
            "basis_weight_kg": None,
            "basis_quantity": 1,
            "method": "",
            "is_active": True,
            "lines": [
                {
                    "ingredient": self.menu.flour.pk,
                    "semi_product": None,
                    "quantity": "100",
                    "quantity_unit": "g",
                    "loss_percent": "0",
                }
            ],
            "sections": [],
            "modifier_groups": [],
            "modifier_lines": [],
        }

    def test_assign_category(self):
        category = IngredientCategory.objects.create(name="Dry")
        sugar = self.menu.sugar
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/menu/ingredients/assign-category/",
            {"ids": [self.flour.pk, sugar.pk], "category": category.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 204, response.content)
        self.flour.refresh_from_db()
        sugar.refresh_from_db()
        self.assertEqual(self.flour.category_id, category.pk)
        self.assertEqual(sugar.category_id, category.pk)
        self.assertEqual(self.flour.avg_cost, Decimal("0.010000"))
        self.assertEqual(sugar.avg_cost, Decimal("0.005000"))

        response = self.client.post(
            "/api/menu/ingredients/assign-category/",
            {"ids": [self.flour.pk], "category": None},
            format="json",
        )
        self.assertEqual(response.status_code, 204, response.content)
        self.flour.refresh_from_db()
        self.assertIsNone(self.flour.category_id)
        self.assertEqual(self.flour.avg_cost, Decimal("0.010000"))

        response = self.client.post(
            "/api/menu/ingredients/assign-category/",
            {"ids": [999999], "category": category.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)

        response = self.client.post(
            "/api/menu/ingredients/assign-category/",
            {"ids": [self.flour.pk], "category": 999999},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)

        response = self.client.post(
            "/api/menu/ingredients/assign-category/",
            {"ids": [], "category": category.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_assign_tech_card_category(self):
        category = TechCardCategory.objects.create(name="Cakes")
        bento = self.menu.bento
        cake = self.menu.cake
        bento.sale_price = Decimal("25.00")
        bento.save(update_fields=["sale_price"])
        bento_lines = bento.lines.count()
        cake_lines = cake.lines.count()
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/menu/tech-cards/assign-category/",
            {"ids": [bento.pk, cake.pk], "category": category.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 204, response.content)
        bento.refresh_from_db()
        cake.refresh_from_db()
        self.assertEqual(bento.category_id, category.pk)
        self.assertEqual(cake.category_id, category.pk)
        self.assertEqual(bento.sale_price, Decimal("25.00"))
        self.assertEqual(bento.lines.count(), bento_lines)
        self.assertEqual(cake.lines.count(), cake_lines)

        response = self.client.post(
            "/api/menu/tech-cards/assign-category/",
            {"ids": [bento.pk], "category": None},
            format="json",
        )
        self.assertEqual(response.status_code, 204, response.content)
        bento.refresh_from_db()
        self.assertIsNone(bento.category_id)
        self.assertEqual(bento.sale_price, Decimal("25.00"))
        self.assertEqual(bento.lines.count(), bento_lines)

        response = self.client.post(
            "/api/menu/tech-cards/assign-category/",
            {"ids": [999999], "category": category.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_tech_card_sale_price(self):
        self.client.force_authenticate(self.staff)
        payload = self._bento_payload()
        payload["sale_price"] = "25.00"
        response = self.client.put(
            f"/api/menu/tech-cards/{self.menu.bento.pk}/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Decimal(response.json()["sale_price"]), Decimal("25.00"))
        self.menu.bento.refresh_from_db()
        self.assertEqual(self.menu.bento.sale_price, Decimal("25.00"))

        del payload["sale_price"]
        response = self.client.put(
            f"/api/menu/tech-cards/{self.menu.bento.pk}/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.menu.bento.refresh_from_db()
        self.assertEqual(self.menu.bento.sale_price, Decimal("25.00"))

        payload["sale_price"] = None
        response = self.client.put(
            f"/api/menu/tech-cards/{self.menu.bento.pk}/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(response.json()["sale_price"])
        self.menu.bento.refresh_from_db()
        self.assertIsNone(self.menu.bento.sale_price)
