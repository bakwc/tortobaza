import io
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from accounts.permissions import grant
from catalog.auto_translate import (
    TRANSLATE_MODEL,
    TRANSLATE_PROMPT,
    FieldTranslation,
    ItemTranslation,
    TranslationBatch,
    translate_saved,
)
from catalog.models import Category, CategoryLanding, Option, OptionGroup, Product, ProductImage


class _ImmediateThread:
    def __init__(self, target, args, daemon):
        self._target = target
        self._args = args

    def start(self):
        self._target(*self._args)


def reply_for(by_kind: dict[str, dict[str, dict[str, str]]]):
    def respond(**kwargs):
        sent = json.loads(kwargs["input"])
        spec = {
            item["key"]: {field: by_kind[item["kind"]][field] for field in item["fields"]}
            for item in sent["items"]
        }
        return type("Response", (), {"output_parsed": batch(spec)})()

    return respond


def batch(spec: dict[str, dict[str, dict[str, str]]]) -> TranslationBatch:
    return TranslationBatch(
        items=[
            ItemTranslation(
                key=key,
                fields=[FieldTranslation(field=field, **langs) for field, langs in fields.items()],
            )
            for key, fields in spec.items()
        ]
    )


def jpeg() -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), color=(10, 20, 30)).save(buf, format="JPEG")
    return SimpleUploadedFile("p.jpg", buf.getvalue(), content_type="image/jpeg")


@patch("catalog.auto_translate.threading.Thread", _ImmediateThread)
@patch("catalog.auto_translate.OpenAI")
class AutoTranslateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        editor = User.objects.create_user(username="site-edit", password="password")
        grant(editor, "edit_catalog")
        self.client.force_authenticate(user=editor)
        self.category = Category.objects.create(
            slug="cakes",
            name_en="Cakes",
            name_ka="ტორტები",
            name_ru="Торты",
            page_slug_en="cakes",
        )

    def test_category_translates_every_filled_field_and_suffixes_page_slug(self, openai_cls):
        CategoryLanding.objects.create(
            slug="taken-landing",
            source=self.category,
            page_slug_ka="bento",
        )
        openai_cls.return_value.responses.parse.side_effect = reply_for(
            {
                "category": {
                    "name": {"en": "Bento cakes", "ka": "ბენტო ტორტები", "ru": "Бенто-торты"},
                    "page_heading": {"en": "Bento", "ka": "ბენტო", "ru": "Бенто"},
                    "page_slug": {"en": "Bento", "ka": "bento-tortebi", "ru": "bento-torty"},
                }
            }
        )
        with self.captureOnCommitCallbacks(execute=True):
            created = self.client.post(
                "/api/site/categories/",
                {
                    "slug": "bento",
                    "name_en": "",
                    "name_ka": "",
                    "name_ru": "Бенто-торты",
                    "page_slug_en": "",
                    "page_slug_ka": "",
                    "page_slug_ru": "bento-torty",
                    "page_heading_en": "",
                    "page_heading_ka": "",
                    "page_heading_ru": "Бенто",
                    "position": 0,
                    "is_active": True,
                    "delivery_schedule_tier": "same_day",
                },
                format="json",
            )
        self.assertEqual(created.status_code, 201, created.content)
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertEqual(call["model"], TRANSLATE_MODEL)
        self.assertEqual(call["instructions"], TRANSLATE_PROMPT)
        self.assertIs(call["text_format"], TranslationBatch)
        self.assertFalse(call["store"])
        sent = json.loads(call["input"])["items"]
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["kind"], "category")
        self.assertEqual(
            sent[0]["fields"],
            {
                "name": {"ru": "Бенто-торты"},
                "page_heading": {"ru": "Бенто"},
                "page_slug": {"ru": "bento-torty"},
            },
        )
        row = Category.objects.get(pk=created.json()["id"])
        self.assertEqual(row.name_en, "Bento cakes")
        self.assertEqual(row.name_ka, "ბენტო ტორტები")
        self.assertEqual(row.name_ru, "Бенто-торты")
        self.assertEqual(row.page_heading_en, "Bento")
        self.assertEqual(row.page_heading_ka, "ბენტო")
        self.assertEqual(row.page_slug_en, "bento-2")
        self.assertEqual(row.page_slug_ka, "bento-tortebi")
        self.assertEqual(row.page_slug_ru, "bento-torty")
        self.assertFalse(row.page_description_en)

    def test_product_and_image_alt_go_in_one_request(self, openai_cls):
        product = Product.objects.create(
            category=self.category,
            slug="medovik",
            name_en="Honey cake",
            name_ka="თაფლის ტორტი",
            name_ru="Медовик",
            description_en="",
            description_ka="",
            description_ru="",
            base_price=Decimal("120.00"),
        )
        image = ProductImage.objects.create(product=product, image=jpeg(), alt_ru="Торт на столе")
        openai_cls.return_value.responses.parse.side_effect = reply_for(
            {
                "product": {
                    "name": {"en": "Medovik", "ka": "მედოვიკი", "ru": "Медовик"},
                    "description": {"en": "Honey layers", "ka": "თაფლის ფენები", "ru": "Медовые коржи"},
                },
                "productimage": {
                    "alt": {"en": "Cake on a table", "ka": "ტორტი მაგიდაზე", "ru": "Торт на столе"},
                },
            }
        )
        with self.captureOnCommitCallbacks(execute=True):
            updated = self.client.put(
                f"/api/site/products/{product.pk}/",
                {
                    "slug": "medovik",
                    "name_en": "",
                    "name_ka": "",
                    "name_ru": "Медовик",
                    "description_en": "",
                    "description_ka": "",
                    "description_ru": "Медовые коржи",
                    "base_price": "120.00",
                    "category": self.category.pk,
                    "delivery_schedule_tier": None,
                    "tech_card": None,
                    "position": 0,
                    "is_active": True,
                    "option_groups": [],
                },
                format="json",
            )
        self.assertEqual(updated.status_code, 200, updated.content)
        sent = json.loads(openai_cls.return_value.responses.parse.call_args.kwargs["input"])
        self.assertEqual(
            [(item["key"], item["kind"]) for item in sent["items"]],
            [(f"product:{product.pk}", "product"), (f"productimage:{image.pk}", "productimage")],
        )
        self.assertEqual(
            sent["items"][0]["fields"],
            {"name": {"ru": "Медовик"}, "description": {"ru": "Медовые коржи"}},
        )
        self.assertEqual(sent["items"][1]["fields"], {"alt": {"ru": "Торт на столе"}})
        product.refresh_from_db()
        image.refresh_from_db()
        self.assertEqual(product.name_en, "Medovik")
        self.assertEqual(product.name_ka, "მედოვიკი")
        self.assertEqual(product.name_ru, "Медовик")
        self.assertEqual(product.description_en, "Honey layers")
        self.assertEqual(product.description_ru, "Медовые коржи")
        self.assertEqual(image.alt_en, "Cake on a table")
        self.assertEqual(image.alt_ka, "ტორტი მაგიდაზე")
        self.assertEqual(image.alt_ru, "Торт на столе")

    def test_option_group_translates_group_and_options(self, openai_cls):
        openai_cls.return_value.responses.parse.side_effect = reply_for(
            {
                "optiongroup": {"name": {"en": "Size", "ka": "ზომა", "ru": "Размер"}},
                "option": {"name": {"en": "Small", "ka": "პატარა", "ru": "Малый"}},
            }
        )
        with self.captureOnCommitCallbacks(execute=True):
            created = self.client.post(
                "/api/site/option-groups/",
                {
                    "slug": "size",
                    "name_en": "",
                    "name_ka": "",
                    "name_ru": "Размер",
                    "selection_type": "single",
                    "is_required_default": True,
                    "min_selections": 0,
                    "max_selections": 1,
                    "options": [
                        {
                            "name_en": "",
                            "name_ka": "",
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
        group = OptionGroup.objects.get(pk=created.json()["id"])
        option = Option.objects.get(group=group)
        sent = json.loads(openai_cls.return_value.responses.parse.call_args.kwargs["input"])
        self.assertEqual(
            [item["key"] for item in sent["items"]],
            [f"optiongroup:{group.pk}", f"option:{option.pk}"],
        )
        self.assertEqual(group.name_en, "Size")
        self.assertEqual(group.name_ka, "ზომა")
        self.assertEqual(group.name_ru, "Размер")
        self.assertEqual(option.name_en, "Small")
        self.assertEqual(option.name_ka, "პატარა")
        self.assertEqual(option.name_ru, "Малый")

    def test_landing_translates_missing_page_slug(self, openai_cls):
        openai_cls.return_value.responses.parse.side_effect = reply_for(
            {
                "categorylanding": {
                    "page_heading": {"en": "Wedding cakes", "ka": "საქორწილო ტორტები", "ru": "Свадебные торты"},
                    "page_slug": {"en": "wedding-cakes", "ka": "sakortsilo-tortebi", "ru": "svadebnye-torty"},
                }
            }
        )
        with self.captureOnCommitCallbacks(execute=True):
            created = self.client.post(
                "/api/site/category-landings/",
                {
                    "slug": "wedding",
                    "source": self.category.pk,
                    "page_slug_en": "",
                    "page_slug_ka": "",
                    "page_slug_ru": "svadebnye-torty",
                    "page_heading_en": "",
                    "page_heading_ka": "",
                    "page_heading_ru": "Свадебные торты",
                    "is_active": True,
                },
                format="json",
            )
        self.assertEqual(created.status_code, 201, created.content)
        row = CategoryLanding.objects.get(pk=created.json()["id"])
        self.assertEqual(row.page_heading_en, "Wedding cakes")
        self.assertEqual(row.page_heading_ka, "საქორწილო ტორტები")
        self.assertEqual(row.page_slug_en, "wedding-cakes")
        self.assertEqual(row.page_slug_ka, "sakortsilo-tortebi")
        self.assertEqual(row.page_slug_ru, "svadebnye-torty")

    def test_changed_source_is_kept(self, openai_cls):
        category = Category.objects.create(slug="bento", name_en="", name_ka="", name_ru="Бенто")

        def edit_meanwhile(**kwargs):
            Category.objects.filter(pk=category.pk).update(name_ru="Бенто-торты")
            return type(
                "Response",
                (),
                {
                    "output_parsed": batch(
                        {
                            f"category:{category.pk}": {
                                "name": {"en": "Bento", "ka": "ბენტო", "ru": "Бенто"},
                            }
                        }
                    )
                },
            )()

        openai_cls.return_value.responses.parse.side_effect = edit_meanwhile
        translate_saved([(Category, category.pk)])
        category.refresh_from_db()
        self.assertEqual(category.name_en, "")
        self.assertEqual(category.name_ka, "")
        self.assertEqual(category.name_ru, "Бенто-торты")

    def test_complete_record_is_not_sent(self, openai_cls):
        with self.captureOnCommitCallbacks(execute=True):
            created = self.client.post(
                "/api/site/categories/",
                {
                    "slug": "bento",
                    "name_en": "Bento",
                    "name_ka": "ბენტო",
                    "name_ru": "Бенто",
                    "position": 0,
                    "is_active": True,
                    "delivery_schedule_tier": "same_day",
                },
                format="json",
            )
        self.assertEqual(created.status_code, 201, created.content)
        openai_cls.assert_not_called()

    def test_translate_endpoint_returns_every_field_without_saving(self, openai_cls):
        openai_cls.return_value.responses.parse.side_effect = reply_for(
            {
                "category": {
                    "name": {"en": "Napoleon", "ka": "ნაპოლეონი", "ru": "Наполеон торт"},
                    "page_slug": {"en": "cakes", "ka": "napoleoni", "ru": "napoleon"},
                },
                "product": {
                    "description": {"en": "Puff pastry", "ka": "ფენოვანი ცომი", "ru": "Слоёное тесто"},
                },
            }
        )
        response = self.client.post(
            "/api/site/translate/",
            {
                "language": "ru",
                "items": [
                    {
                        "key": "category",
                        "kind": "category",
                        "id": None,
                        "fields": {"name": " Наполеон ", "page_slug": "napoleon"},
                    },
                    {
                        "key": "product",
                        "kind": "product",
                        "id": None,
                        "fields": {"description": "Слоёное тесто"},
                    },
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            response.json()["items"],
            [
                {
                    "key": "category",
                    "fields": {
                        "name": {"en": "Napoleon", "ka": "ნაპოლეონი", "ru": " Наполеон "},
                        "page_slug": {"en": "cakes-2", "ka": "napoleoni", "ru": "napoleon"},
                    },
                },
                {
                    "key": "product",
                    "fields": {
                        "description": {"en": "Puff pastry", "ka": "ფენოვანი ცომი", "ru": "Слоёное тесто"},
                    },
                },
            ],
        )
        self.assertFalse(Product.objects.exists())
        self.assertFalse(Category.objects.filter(slug="napoleon").exists())

    def test_translate_endpoint_requires_edit_permission(self, openai_cls):
        viewer = User.objects.create_user(username="site-view", password="password")
        grant(viewer, "view_catalog")
        self.client.force_authenticate(user=viewer)
        response = self.client.post(
            "/api/site/translate/",
            {
                "language": "ru",
                "items": [{"key": "category", "kind": "category", "id": None, "fields": {"name": "Торты"}}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        openai_cls.assert_not_called()

    def test_option_without_a_name_is_rejected(self, openai_cls):
        response = self.client.post(
            "/api/site/option-groups/",
            {
                "slug": "size",
                "name_en": "",
                "name_ka": "",
                "name_ru": "Размер",
                "selection_type": "single",
                "is_required_default": True,
                "min_selections": 0,
                "max_selections": 1,
                "options": [
                    {
                        "name_en": " ",
                        "name_ka": "",
                        "name_ru": "",
                        "price_delta": "0.00",
                        "position": 0,
                        "is_active": True,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(OptionGroup.objects.filter(slug="size").exists())
        openai_cls.assert_not_called()

    def test_mismatched_model_output_raises(self, openai_cls):
        category = Category.objects.create(slug="bento", name_en="", name_ka="", name_ru="Бенто")
        openai_cls.return_value.responses.parse.return_value.output_parsed = batch(
            {"other": {"name": {"en": "Bento", "ka": "ბენტო", "ru": "Бенто"}}}
        )
        with self.assertRaises(RuntimeError):
            translate_saved([(Category, category.pk)])
        category.refresh_from_db()
        self.assertEqual(category.name_en, "")

    def test_empty_model_output_raises(self, openai_cls):
        category = Category.objects.create(slug="bento", name_en="", name_ka="", name_ru="Бенто")
        openai_cls.return_value.responses.parse.return_value.output_parsed = None
        with self.assertRaises(RuntimeError):
            translate_saved([(Category, category.pk)])
        category.refresh_from_db()
        self.assertEqual(category.name_en, "")
