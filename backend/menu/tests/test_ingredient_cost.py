from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
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
