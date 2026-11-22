from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.permissions import grant
from crm.models import FinancialAccount, FinancialTransaction
from inventory.models import StockMovement, Supplier, Supply
from menu.tests.fixtures import MenuFixture


class InventoryApiTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        self.client = APIClient()
        self.staff = User.objects.create_user("chef", password="x")
        self.admin = User.objects.create_user("boss", password="x")
        grant(self.staff, "edit_inventory", "edit_menu")
        grant(self.admin, "edit_inventory", "view_costs")
        self.account = FinancialAccount.objects.create(name="BOG", kind=FinancialAccount.KIND_BANK)

    def _supply_payload(self, transaction_ids: list[int]) -> dict:
        return {
            "date": "2026-10-01",
            "supplier": None,
            "financial_transactions": transaction_ids,
            "comment": "",
            "lines": [{"ingredient": self.menu.flour.pk, "quantity": "1000", "total": "10.00"}],
            "receipts": [],
        }

    def test_supplies_require_finance_admin(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post("/api/inventory/supplies/", self._supply_payload([]), format="json")
        self.assertEqual(response.status_code, 403)

    def test_supply_links_product_expense(self):
        first = FinancialTransaction.objects.create(
            account=self.account,
            date="2026-10-01",
            amount=Decimal("-6.00"),
            kind=FinancialTransaction.KIND_EXPENSE,
            expense_type=FinancialTransaction.EXPENSE_PRODUCTS,
        )
        second = FinancialTransaction.objects.create(
            account=self.account,
            date="2026-10-01",
            amount=Decimal("-4.00"),
            kind=FinancialTransaction.KIND_EXPENSE,
            expense_type=FinancialTransaction.EXPENSE_PRODUCTS,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/inventory/supplies/",
            self._supply_payload([first.pk, second.pk]),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(
            set(Supply.objects.get().financial_transactions.values_list("pk", flat=True)),
            {first.pk, second.pk},
        )
        self.assertEqual(StockMovement.objects.get().quantity, Decimal("1000"))
        self.assertEqual(
            {row["id"] for row in response.json()["financial_transactions"]},
            {first.pk, second.pk},
        )

    def test_supply_rejects_non_product_expense(self):
        transaction = FinancialTransaction.objects.create(
            account=self.account,
            date="2026-10-01",
            amount=Decimal("-10.00"),
            kind=FinancialTransaction.KIND_EXPENSE,
            expense_type=FinancialTransaction.EXPENSE_RENT,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/inventory/supplies/", self._supply_payload([transaction.pk]), format="json")
        self.assertEqual(response.status_code, 400)

    def test_supply_creates_product_expense(self):
        grant(self.admin, "edit_finance")
        supplier = Supplier.objects.create(name="Молочный")
        self.client.force_authenticate(self.admin)
        payload = self._supply_payload([])
        payload["supplier"] = supplier.pk
        payload["new_financial_transaction"] = {
            "account_id": self.account.pk,
            "amount": "10.00",
            "description": "мука",
        }
        response = self.client.post("/api/inventory/supplies/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        transaction = FinancialTransaction.objects.get()
        self.assertEqual(transaction.account_id, self.account.pk)
        self.assertEqual(transaction.kind, FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(transaction.expense_type, FinancialTransaction.EXPENSE_PRODUCTS)
        self.assertEqual(transaction.amount, Decimal("-10.00"))
        self.assertEqual(transaction.date.isoformat(), "2026-10-01")
        self.assertEqual(transaction.counterparty_name, "Молочный")
        self.assertEqual(transaction.description, "мука")
        supply = Supply.objects.get()
        self.assertEqual(supply.financial_transactions.get().pk, transaction.pk)
        self.assertEqual(response.json()["financial_transactions"][0]["id"], transaction.pk)

    def test_supply_rejects_unknown_payment_account(self):
        grant(self.admin, "edit_finance")
        self.client.force_authenticate(self.admin)
        payload = self._supply_payload([])
        payload["new_financial_transaction"] = {
            "account_id": self.account.pk + 1,
            "amount": "10.00",
            "description": "",
        }
        response = self.client.post("/api/inventory/supplies/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FinancialTransaction.objects.count(), 0)
        self.assertEqual(Supply.objects.count(), 0)

    def test_supply_update_rejects_new_payment(self):
        grant(self.admin, "edit_finance")
        self.client.force_authenticate(self.admin)
        created = self.client.post("/api/inventory/supplies/", self._supply_payload([]), format="json")
        self.assertEqual(created.status_code, 201, created.content)
        payload = self._supply_payload([])
        payload["new_financial_transaction"] = {
            "account_id": self.account.pk,
            "amount": "10.00",
            "description": "",
        }
        response = self.client.put(
            f"/api/inventory/supplies/{created.json()['id']}/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FinancialTransaction.objects.count(), 0)

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
