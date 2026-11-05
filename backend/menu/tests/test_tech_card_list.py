from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.permissions import grant
from menu.models import UNIT_MILLILITER, TechCardLine, TechCardSection
from menu.tests.fixtures import MenuFixture


class TechCardListLiteTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        self.menu.cake.sale_price = Decimal("120.00")
        self.menu.cake.save()
        self.menu.extras.is_global = True
        self.menu.extras.save()
        section = TechCardSection.objects.create(tech_card=self.menu.cake, name="Cream", method="")
        TechCardLine.objects.create(
            tech_card=self.menu.cake,
            section=section,
            ingredient=self.menu.cream,
            quantity=Decimal("10"),
            quantity_unit=UNIT_MILLILITER,
        )
        self.client = APIClient()
        user = User.objects.create_user(username="menu", password="password")
        grant(user, "view_menu")
        self.client.force_authenticate(user=user)

    def test_lite_list_has_counts_and_no_costs(self):
        response = self.client.get("/api/menu/tech-cards/lite/")
        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.json() if item["name"] == "Cake")
        self.assertEqual(row["sale_price"], "120.00")
        self.assertEqual(row["components_count"], 3)
        self.assertEqual(row["sections_count"], 1)
        self.assertEqual(row["groups_count"], 2)
        self.assertEqual(row["images"], [])
        self.assertNotIn("base_cost", row)
        self.assertNotIn("cost_min", row)
        self.assertNotIn("cost_max", row)
        self.assertNotIn("lines", row)
        self.assertNotIn("modifier_groups", row)
