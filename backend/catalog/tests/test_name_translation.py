import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.permissions import grant
from catalog.models import Category, Product
from catalog.name_translation import (
    NAME_TRANSLATE_MODEL,
    NAME_TRANSLATE_PROMPT,
    TranslatedName,
    translate_names,
)


class _ImmediateThread:
    def __init__(self, target, args, daemon):
        self._target = target
        self._args = args

    def start(self):
        self._target(*self._args)


def _category_body(**names) -> dict:
    body = {
        "slug": "bento",
        "name_en": "",
        "name_ka": "",
        "name_ru": "",
        "position": 0,
        "is_active": True,
        "delivery_schedule_tier": "same_day",
    }
    body.update(names)
    return body


@patch("catalog.name_translation.threading.Thread", _ImmediateThread)
@patch("catalog.name_translation.OpenAI")
class NameTranslationTests(TestCase):
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
        )

    def _product_body(self, **names) -> dict:
        body = {
            "slug": "medovik",
            "name_en": "",
            "name_ka": "",
            "name_ru": "",
            "description_en": "",
            "description_ka": "",
            "description_ru": "",
            "base_price": "120.00",
            "category": self.category.pk,
            "delivery_schedule_tier": None,
            "tech_card": None,
            "position": 0,
            "is_active": True,
            "option_groups": [],
        }
        body.update(names)
        return body

    def test_new_category_gets_missing_names(self, openai_cls):
        openai_cls.return_value.responses.parse.return_value.output_parsed = TranslatedName(
            en="Bento cakes", ka="ბენტო ტორტები", ru="Бенто-торты"
        )
        with self.captureOnCommitCallbacks(execute=True):
            created = self.client.post(
                "/api/site/categories/", _category_body(name_ru="Бенто-торты"), format="json"
            )
        self.assertEqual(created.status_code, 201, created.content)
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertEqual(call["model"], NAME_TRANSLATE_MODEL)
        self.assertEqual(call["instructions"], NAME_TRANSLATE_PROMPT)
        self.assertIs(call["text_format"], TranslatedName)
        self.assertFalse(call["store"])
        self.assertEqual(
            json.loads(call["input"]),
            {"kind": "category", "names": {"ru": "Бенто-торты"}},
        )
        row = Category.objects.get(pk=created.json()["id"])
        self.assertEqual(row.name_en, "Bento cakes")
        self.assertEqual(row.name_ka, "ბენტო ტორტები")
        self.assertEqual(row.name_ru, "Бенто-торты")

    def test_new_product_keeps_filled_names(self, openai_cls):
        openai_cls.return_value.responses.parse.return_value.output_parsed = TranslatedName(
            en="Honey Cake", ka="მედოვიკი", ru="Медовик (перевод)"
        )
        with self.captureOnCommitCallbacks(execute=True):
            created = self.client.post(
                "/api/site/products/",
                self._product_body(name_en="Honey Cake", name_ru="Медовик"),
                format="json",
            )
        self.assertEqual(created.status_code, 201, created.content)
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertEqual(
            json.loads(call["input"]),
            {"kind": "product", "names": {"en": "Honey Cake", "ru": "Медовик"}},
        )
        row = Product.objects.get(pk=created.json()["id"])
        self.assertEqual(row.name_en, "Honey Cake")
        self.assertEqual(row.name_ka, "მედოვიკი")
        self.assertEqual(row.name_ru, "Медовик")

    def test_cleared_name_is_translated_again_on_edit(self, openai_cls):
        product = Product.objects.create(
            category=self.category,
            slug="medovik",
            name_en="Honey cake",
            name_ka="თაფლის ტორტი",
            name_ru="Медовик",
            base_price="120.00",
        )
        openai_cls.return_value.responses.parse.return_value.output_parsed = TranslatedName(
            en="Medovik", ka="მედოვიკი", ru="Медовик"
        )
        with self.captureOnCommitCallbacks(execute=True):
            updated = self.client.put(
                f"/api/site/products/{product.pk}/",
                self._product_body(name_en="Honey cake", name_ru="Медовик"),
                format="json",
            )
        self.assertEqual(updated.status_code, 200, updated.content)
        product.refresh_from_db()
        self.assertEqual(product.name_en, "Honey cake")
        self.assertEqual(product.name_ka, "მედოვიკი")
        self.assertEqual(product.name_ru, "Медовик")

    def test_all_names_filled_skips_translation(self, openai_cls):
        with self.captureOnCommitCallbacks(execute=True):
            created = self.client.post(
                "/api/site/categories/",
                _category_body(name_en="Bento", name_ka="ბენტო", name_ru="Бенто"),
                format="json",
            )
        self.assertEqual(created.status_code, 201, created.content)
        openai_cls.assert_not_called()

    def test_no_name_is_rejected(self, openai_cls):
        created = self.client.post(
            "/api/site/categories/", _category_body(name_ru="  "), format="json"
        )
        self.assertEqual(created.status_code, 400)
        self.assertFalse(Category.objects.filter(slug="bento").exists())
        openai_cls.assert_not_called()

    def test_names_changed_during_translation_are_kept(self, openai_cls):
        category = Category.objects.create(slug="bento", name_en="", name_ka="", name_ru="Бенто")

        def edit_meanwhile(**kwargs):
            Category.objects.filter(pk=category.pk).update(name_ru="Бенто-торты")
            return type("Response", (), {"output_parsed": TranslatedName(en="Bento", ka="ბენტო", ru="Бенто")})()

        openai_cls.return_value.responses.parse.side_effect = edit_meanwhile
        translate_names(Category, category.pk)
        category.refresh_from_db()
        self.assertEqual(category.name_en, "")
        self.assertEqual(category.name_ka, "")
        self.assertEqual(category.name_ru, "Бенто-торты")

    def test_translate_endpoint_returns_all_languages_without_saving(self, openai_cls):
        openai_cls.return_value.responses.parse.return_value.output_parsed = TranslatedName(
            en="Napoleon", ka="ნაპოლეონი", ru="Наполеон торт"
        )
        response = self.client.post(
            "/api/site/translate-name/",
            {"kind": "product", "language": "ru", "name": " Наполеон "},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {"en": "Napoleon", "ka": "ნაპოლეონი", "ru": "Наполеон"})
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertEqual(
            json.loads(call["input"]),
            {"kind": "product", "names": {"ru": "Наполеон"}},
        )
        self.assertFalse(Product.objects.exists())

    def test_translate_endpoint_requires_edit_permission(self, openai_cls):
        viewer = User.objects.create_user(username="site-view", password="password")
        grant(viewer, "view_catalog")
        self.client.force_authenticate(user=viewer)
        response = self.client.post(
            "/api/site/translate-name/",
            {"kind": "category", "language": "ru", "name": "Торты"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        openai_cls.assert_not_called()

    def test_empty_model_output_raises(self, openai_cls):
        category = Category.objects.create(slug="bento", name_en="", name_ka="", name_ru="Бенто")
        openai_cls.return_value.responses.parse.return_value.output_parsed = None
        with self.assertRaises(RuntimeError):
            translate_names(Category, category.pk)
        category.refresh_from_db()
        self.assertEqual(category.name_en, "")
