import io

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from accounts.permissions import grant
from catalog.models import Category, OptionGroup, Product, ProductImage, ProductOptionGroup


class SiteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(username="site-view", password="password")
        self.editor = User.objects.create_user(username="site-edit", password="password")
        grant(self.viewer, "view_catalog")
        grant(self.editor, "edit_catalog")
        self.category = Category.objects.create(
            name="Cakes",
            slug="cakes-site",
            name_en="Cakes",
            name_ka="Cakes",
            name_ru="Торты",
        )
        self.group = OptionGroup.objects.create(
            slug="filling-site",
            name_en="Filling",
            name_ka="Filling",
            name_ru="Начинка",
            selection_type="single",
            is_required_default=True,
            min_selections=0,
            max_selections=1,
        )

    def test_viewer_can_list_but_not_create(self):
        self.client.force_authenticate(user=self.viewer)
        listed = self.client.get("/api/site/products/")
        self.assertEqual(listed.status_code, 200)
        created = self.client.post(
            "/api/site/products/",
            {
                "slug": "new-cake",
                "name_en": "New",
                "name_ka": "New",
                "name_ru": "Новый",
                "description_en": "",
                "description_ka": "",
                "description_ru": "",
                "base_price": "50.00",
                "category": self.category.pk,
                "position": 0,
                "is_active": True,
                "option_groups": [],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 403)

    def test_product_crud_with_option_groups(self):
        self.client.force_authenticate(user=self.editor)
        created = self.client.post(
            "/api/site/products/",
            {
                "slug": "medovik-site",
                "name_en": "Honey",
                "name_ka": "Honey",
                "name_ru": "Медовик",
                "description_en": "Tasty",
                "description_ka": "Tasty",
                "description_ru": "Вкусный",
                "base_price": "120.00",
                "category": self.category.pk,
                "delivery_schedule_tier": None,
                "tech_card": None,
                "position": 1,
                "is_active": True,
                "option_groups": [
                    {"option_group": self.group.pk, "position": 0, "is_required": True}
                ],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        product_id = created.json()["id"]
        self.assertEqual(
            ProductOptionGroup.objects.filter(product_id=product_id).count(),
            1,
        )
        detail = self.client.get(f"/api/site/products/{product_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.json()["option_groups"]), 1)
        self.assertTrue(
            ProductOptionGroup.objects.filter(
                product_id=product_id, option_group_id=self.group.pk
            ).exists()
        )
        updated = self.client.put(
            f"/api/site/products/{product_id}/",
            {
                "slug": "medovik-site",
                "name_en": "Honey cake",
                "name_ka": "Honey cake",
                "name_ru": "Медовик",
                "description_en": "Tasty",
                "description_ka": "Tasty",
                "description_ru": "Вкусный",
                "base_price": "130.00",
                "category": self.category.pk,
                "delivery_schedule_tier": None,
                "tech_card": None,
                "position": 1,
                "is_active": True,
                "option_groups": [],
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["base_price"], "130.00")
        self.assertEqual(ProductOptionGroup.objects.filter(product_id=product_id).count(), 0)

    def test_product_image_upload_and_crop_patch(self):
        product = Product.objects.create(
            category=self.category,
            name="Img",
            slug="img-product",
            description="",
            base_price=Decimal("10.00"),
        )
        buf = io.BytesIO()
        Image.new("RGB", (600, 600), color=(10, 20, 30)).save(buf, format="JPEG")
        buf.seek(0)
        upload = SimpleUploadedFile("p.jpg", buf.read(), content_type="image/jpeg")
        self.client.force_authenticate(user=self.editor)
        posted = self.client.post(
            f"/api/site/products/{product.pk}/images/",
            {
                "image": upload,
                "crop_left": "0.1",
                "crop_top": "0.2",
                "crop_size": "0.8",
                "alt_en": "Alt",
                "alt_ka": "",
                "alt_ru": "",
            },
            format="multipart",
        )
        self.assertEqual(posted.status_code, 201, posted.content)
        image_id = posted.json()["id"]
        self.assertAlmostEqual(posted.json()["crop_left"], 0.1)
        patched = self.client.patch(
            f"/api/site/products/{product.pk}/images/{image_id}/",
            {"crop_left": 0.0, "crop_top": 0.0, "crop_size": 1.0},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        row = ProductImage.objects.get(pk=image_id)
        self.assertEqual(row.crop_size, 1.0)

    def test_option_group_nested_save(self):
        self.client.force_authenticate(user=self.editor)
        created = self.client.post(
            "/api/site/option-groups/",
            {
                "slug": "size-site",
                "name_en": "Size",
                "name_ka": "Size",
                "name_ru": "Размер",
                "selection_type": "single",
                "is_required_default": True,
                "min_selections": 1,
                "max_selections": 1,
                "options": [
                    {
                        "name_en": "Small",
                        "name_ka": "Small",
                        "name_ru": "Малый",
                        "price_delta": "0.00",
                        "weight_kg": None,
                        "position": 0,
                        "is_active": True,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        group_id = created.json()["id"]
        self.assertEqual(len(created.json()["options"]), 1)
