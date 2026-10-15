from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from crm.models import FinancialAccount, FinancialTransaction
from inventory.models import StockMovement, Supply
from menu.tests.fixtures import MenuFixture


class InventoryApiTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        self.client = APIClient()
        self.staff = User.objects.create_user("chef", password="x")
        self.admin = User.objects.create_user("boss", password="x")
        UserProfile.objects.create(user=self.admin, is_finance_admin=True)
        self.account = FinancialAccount.objects.create(name="BOG", kind=FinancialAccount.KIND_BANK)

    def _supply_payload(self, transaction_id: int | None) -> dict:
        return {
            "date": "2026-10-01",
            "supplier": None,
            "financial_transaction": transaction_id,
            "comment": "",
            "lines": [{"ingredient": self.menu.flour.pk, "quantity": "1000", "total": "10.00"}],
        }

    def test_supplies_require_finance_admin(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post("/api/inventory/supplies/", self._supply_payload(None), format="json")
        self.assertEqual(response.status_code, 403)

    def test_supply_links_product_expense(self):
        transaction = FinancialTransaction.objects.create(
            account=self.account,
            date="2026-10-01",
            amount=Decimal("-10.00"),
            kind=FinancialTransaction.KIND_EXPENSE,
            expense_type=FinancialTransaction.EXPENSE_PRODUCTS,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/inventory/supplies/", self._supply_payload(transaction.pk), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Supply.objects.get().financial_transaction, transaction)
        self.assertEqual(StockMovement.objects.get().quantity, Decimal("1000"))
        self.assertEqual(response.json()["financial_transaction"]["id"], transaction.pk)

    def test_supply_rejects_non_product_expense(self):
        transaction = FinancialTransaction.objects.create(
            account=self.account,
            date="2026-10-01",
            amount=Decimal("-10.00"),
            kind=FinancialTransaction.KIND_EXPENSE,
            expense_type=FinancialTransaction.EXPENSE_RENT,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/inventory/supplies/", self._supply_payload(transaction.pk), format="json")
        self.assertEqual(response.status_code, 400)

    def test_staff_records_production_without_costs(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/inventory/productions/",
            {
                "date": "2026-10-02",
                "semi_product": self.menu.frozen_sponge.pk,
                "quantity": "1000",
                "comment": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertNotIn("unit_cost", response.json())
        self.assertEqual(StockMovement.objects.filter(kind=StockMovement.KIND_PRODUCTION_IN).count(), 1)

    def test_stock_hides_costs_from_staff(self):
        self.client.force_authenticate(self.staff)
        staff_rows = self.client.get("/api/inventory/stock/").json()
        self.assertNotIn("avg_cost", staff_rows[0])
        self.client.force_authenticate(self.admin)
        admin_rows = self.client.get("/api/inventory/stock/").json()
        self.assertIn("avg_cost", admin_rows[0])

    def test_used_ingredient_cannot_be_deleted(self):
        self.client.force_authenticate(self.staff)
        response = self.client.delete(f"/api/menu/ingredients/{self.menu.flour.pk}/")
        self.assertEqual(response.status_code, 400)
