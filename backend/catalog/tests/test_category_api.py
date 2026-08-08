from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Category, Product


class CategoryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.active = Category.objects.create(
            name="Wedding",
            slug="wedding",
            page_slug_en="wedding-cakes",
            page_slug_ru="svadebnye-torty",
            page_slug_ka="sartuli-tortebi",
            page_heading_en="Wedding cakes",
            page_heading_ru="Свадебные торты",
            seo_title_en="Wedding cakes Batumi",
            seo_title_ru="Свадебные торты Батуми",
            page_description_en="Handcrafted wedding cakes",
            page_description_ru="Авторские свадебные торты",
            position=1,
            is_active=True,
        )
        self.inactive = Category.objects.create(
            name="Hidden",
            slug="hidden",
            page_slug_en="hidden-cakes",
            page_slug_ru="skrytye-torty",
            page_slug_ka="damalebuli-tortebi",
            position=2,
            is_active=False,
        )
        self.active_product = Product.objects.create(
            category=self.active,
            name="Roses",
            slug="roses",
            description="",
            base_price=Decimal("100.00"),
            is_active=True,
        )
        self.inactive_category_product = Product.objects.create(
            category=self.inactive,
            name="Ghost",
            slug="ghost",
            description="",
            base_price=Decimal("50.00"),
            is_active=True,
        )

    def test_category_detail_en(self):
        response = self.client.get(
            "/api/categories/wedding-cakes/",
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["slug"], "wedding")
        self.assertEqual(data["page_slug"], "wedding-cakes")
        self.assertEqual(data["page_heading"], "Wedding cakes")
        self.assertEqual(data["seo_title"], "Wedding cakes Batumi")
        self.assertEqual(
            data["page_slugs"],
            {
                "en": "wedding-cakes",
                "ru": "svadebnye-torty",
                "ka": "sartuli-tortebi",
            },
        )

    def test_category_detail_ru(self):
        response = self.client.get(
            "/api/categories/svadebnye-torty/",
            HTTP_ACCEPT_LANGUAGE="ru",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["slug"], "wedding")
        self.assertEqual(data["page_slug"], "svadebnye-torty")
        self.assertEqual(data["page_heading"], "Свадебные торты")
        self.assertEqual(data["seo_title"], "Свадебные торты Батуми")

    def test_category_detail_ka(self):
        response = self.client.get(
            "/api/categories/sartuli-tortebi/",
            HTTP_ACCEPT_LANGUAGE="ka",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["slug"], "wedding")

    def test_category_detail_wrong_locale_slug_404(self):
        response = self.client.get(
            "/api/categories/svadebnye-torty/",
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 404)

    def test_inactive_category_404(self):
        response = self.client.get(
            "/api/categories/hidden-cakes/",
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 404)

    def test_products_exclude_inactive_category(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        slugs = {item["slug"] for item in response.json()["results"]}
        self.assertIn("roses", slugs)
        self.assertNotIn("ghost", slugs)

    def test_products_filter_by_category_slug(self):
        response = self.client.get("/api/products/", {"category": "wedding"})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["slug"], "roses")

    def test_products_filter_inactive_category_returns_empty(self):
        response = self.client.get("/api/products/", {"category": "hidden"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_category_list_includes_page_slug(self):
        response = self.client.get("/api/categories/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["page_slug"], "wedding-cakes")
        self.assertEqual(data[0]["page_slugs"]["ru"], "svadebnye-torty")
