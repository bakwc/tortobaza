from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Category, CategoryLanding, Product


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
        self.active_landing = CategoryLanding.objects.create(
            slug="b-day-wedding",
            source=self.active,
            page_slug_en="b-day-cakes",
            page_slug_ru="torty-na-dr",
            page_slug_ka="dabadebis-tortebi",
            page_heading_en="Birthday Wedding Cakes",
            page_heading_ru="Торты на др",
            seo_title_en="Birthday Wedding Cakes Batumi",
            seo_title_ru="Торты на др Батуми",
            page_description_en="Special birthday collection",
            page_description_ru="Специальная коллекция",
            is_active=True,
        )
        self.inactive_landing = CategoryLanding.objects.create(
            slug="inactive-landing",
            source=self.active,
            page_slug_en="inactive-landing-cakes",
            is_active=False,
        )
        self.landing_with_inactive_source = CategoryLanding.objects.create(
            slug="orphan-landing",
            source=self.inactive,
            page_slug_en="orphan-cakes",
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
        self.assertEqual(data["source_page_slug"], "wedding-cakes")
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
        self.assertEqual(data["source_page_slug"], "svadebnye-torty")
        self.assertEqual(data["page_heading"], "Свадебные торты")
        self.assertEqual(data["seo_title"], "Свадебные торты Батуми")

    def test_category_detail_ka(self):
        response = self.client.get(
            "/api/categories/sartuli-tortebi/",
            HTTP_ACCEPT_LANGUAGE="ka",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["slug"], "wedding")

    def test_category_detail_wrong_locale_slug_resolves_category(self):
        response = self.client.get(
            "/api/categories/svadebnye-torty/",
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["page_slug"], "wedding-cakes")

    def test_landing_detail_en(self):
        response = self.client.get(
            "/api/categories/b-day-cakes/",
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["slug"], "wedding")
        self.assertEqual(data["page_slug"], "b-day-cakes")
        self.assertEqual(data["source_page_slug"], "wedding-cakes")
        self.assertEqual(data["page_heading"], "Birthday Wedding Cakes")
        self.assertEqual(data["seo_title"], "Birthday Wedding Cakes Batumi")
        self.assertEqual(
            data["page_slugs"],
            {
                "en": "b-day-cakes",
                "ru": "torty-na-dr",
                "ka": "dabadebis-tortebi",
            },
        )

    def test_landing_detail_ru(self):
        response = self.client.get(
            "/api/categories/torty-na-dr/",
            HTTP_ACCEPT_LANGUAGE="ru",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["slug"], "wedding")
        self.assertEqual(data["page_slug"], "torty-na-dr")
        self.assertEqual(data["source_page_slug"], "svadebnye-torty")
        self.assertEqual(data["page_heading"], "Торты на др")
        self.assertEqual(data["seo_title"], "Торты на др Батуми")

    def test_landing_detail_wrong_locale_slug_resolves_landing(self):
        response = self.client.get(
            "/api/categories/torty-na-dr/",
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["page_slug"], "b-day-cakes")

    def test_inactive_landing_404(self):
        response = self.client.get(
            "/api/categories/inactive-landing-cakes/",
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 404)

    def test_landing_with_inactive_source_404(self):
        response = self.client.get(
            "/api/categories/orphan-cakes/",
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 404)

    def test_landing_not_in_categories_list(self):
        response = self.client.get("/api/categories/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        slugs = [item["page_slug"] for item in data]
        self.assertIn("wedding-cakes", slugs)
        self.assertNotIn("b-day-cakes", slugs)

    def test_landing_in_category_landings_list(self):
        response = self.client.get("/api/category-landings/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["slug"], "b-day-wedding")
        self.assertEqual(data[0]["page_slug"], "b-day-cakes")
        self.assertEqual(
            data[0]["page_slugs"],
            {
                "en": "b-day-cakes",
                "ru": "torty-na-dr",
                "ka": "dabadebis-tortebi",
            },
        )

    def test_landing_slug_collision_with_category_fails_validation(self):
        landing = CategoryLanding(
            slug="collision-landing",
            source=self.active,
            page_slug_en="wedding-cakes",
        )
        with self.assertRaises(ValidationError):
            landing.clean()

    def test_category_slug_collision_with_landing_fails_validation(self):
        category = Category(
            name="Collision Category",
            slug="collision-category",
            page_slug_en="b-day-cakes",
        )
        with self.assertRaises(ValidationError):
            category.clean()

    def test_inactive_category_404(self):
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

    def test_category_detail_wrong_locale_slug_resolves_category(self):
        response = self.client.get(
            "/api/categories/svadebnye-torty/",
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["page_slug"], "wedding-cakes")

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
