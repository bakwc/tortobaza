import tempfile
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from openai.lib._pydantic import to_strict_json_schema
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import UserProfile
from inventory.models import Supplier, Supply, SupplyReceipt
from inventory.receipts import RECEIPT_MODEL, RecognizedLine, RecognizedReceipt, recognize_receipt, to_jpeg
from menu.models import UNIT_GRAM, Ingredient
from menu.tests.fixtures import MenuFixture


def jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


def png_upload() -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (12, 12), "white").save(buffer, format="PNG")
    return SimpleUploadedFile("receipt.png", buffer.getvalue(), content_type="image/png")


def receipt_image() -> ContentFile:
    return ContentFile(jpeg_bytes(), name="receipt.jpg")


def parsed_receipt(ingredient_id: int | None) -> RecognizedReceipt:
    return RecognizedReceipt(
        is_itemized=True,
        merchant_name="Loma",
        date="2026-10-16",
        total=Decimal("11.00"),
        lines=[
            RecognizedLine(
                original_name="ფქვილი 200გრ",
                name_ru="Мука",
                ingredient_id=ingredient_id,
                quantity=Decimal("200"),
                unit="g",
                total=Decimal("11.00"),
            )
        ],
    )


class RecognizeReceiptTests(TestCase):
    def test_structured_schema_accepts_optional_ingredient(self):
        schema = to_strict_json_schema(RecognizedReceipt)
        self.assertEqual(schema["type"], "object")

    @patch("inventory.receipts.OpenAI")
    def test_maps_model_output(self, openai_cls):
        flour = Ingredient.objects.create(name="Мука", unit=UNIT_GRAM)
        Ingredient.objects.create(name="Скрытая мука", unit=UNIT_GRAM, is_active=False)
        openai_cls.return_value.responses.parse.return_value.output_parsed = parsed_receipt(flour.pk)
        recognized = recognize_receipt(jpeg_bytes())
        self.assertEqual(
            recognized,
            {
                "is_itemized": True,
                "merchant_name": "Loma",
                "date": "2026-10-16",
                "total": "11.00",
                "lines": [
                    {
                        "original_name": "ფქვილი 200გრ",
                        "name_ru": "Мука",
                        "ingredient_id": flour.pk,
                        "quantity": "200",
                        "unit": "g",
                        "total": "11.00",
                    }
                ],
            },
        )
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertEqual(call["model"], RECEIPT_MODEL)
        self.assertIs(call["text_format"], RecognizedReceipt)
        self.assertFalse(call["store"])
        catalog = call["input"][0]["content"][0]["text"]
        self.assertIn(f'"id": {flour.pk}', catalog)
        self.assertIn("Мука", catalog)
        self.assertNotIn("Скрытая мука", catalog)
        self.assertTrue(call["input"][0]["content"][1]["image_url"].startswith("data:image/jpeg;base64,"))

    @patch("inventory.receipts.OpenAI")
    def test_unknown_ingredient_id_raises(self, openai_cls):
        Ingredient.objects.create(name="Мука", unit=UNIT_GRAM)
        openai_cls.return_value.responses.parse.return_value.output_parsed = parsed_receipt(999999)
        with self.assertRaises(ValueError):
            recognize_receipt(jpeg_bytes())

    @patch("inventory.receipts.OpenAI")
    def test_empty_model_output_raises(self, openai_cls):
        openai_cls.return_value.responses.parse.return_value.output_parsed = None
        with self.assertRaises(ValueError):
            recognize_receipt(jpeg_bytes())


class SupplyReceiptApiTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.menu = MenuFixture()
        self.client = APIClient()
        self.staff = User.objects.create_user("chef", password="x")
        self.admin = User.objects.create_user("boss", password="x")
        UserProfile.objects.create(user=self.admin, is_finance_admin=True)

    def _recognized(self) -> dict:
        return {
            "is_itemized": True,
            "merchant_name": "Loma",
            "date": "2026-10-16",
            "total": "11.00",
            "lines": [
                {
                    "original_name": "ფქვილი 200გრ",
                    "name_ru": "Мука",
                    "ingredient_id": self.menu.flour.pk,
                    "quantity": "200",
                    "unit": "g",
                    "total": "11.00",
                }
            ],
        }

    def test_png_and_heic_are_stored_as_jpeg(self):
        self.client.force_authenticate(self.admin)
        with patch("inventory.views.recognize_receipt", return_value=self._recognized()):
            png_response = self.client.post("/api/inventory/receipts/", {"image": png_upload()}, format="multipart")
        self.assertEqual(png_response.status_code, 201, png_response.content)
        png_receipt = SupplyReceipt.objects.get()
        self.assertTrue(png_receipt.image.name.endswith(".jpg"))
        with Image.open(png_receipt.image.path) as stored:
            self.assertEqual(stored.format, "JPEG")
        self.assertEqual(png_response.json()["recognized"]["lines"][0]["ingredient_id"], self.menu.flour.pk)
        self.assertIsNone(png_response.json()["recognized"]["supplier"])
        self.assertTrue(png_response.json()["image"].startswith("/media/"))

        heic_path = Path(__file__).resolve().parents[3] / "IMG_0122.HEIC"
        with heic_path.open("rb") as handle:
            heic = SimpleUploadedFile("IMG_0122.HEIC", handle.read(), content_type="image/heic")
        converted = to_jpeg(heic)
        with Image.open(BytesIO(converted.read())) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertLessEqual(max(image.size), 2000)

    def test_supplier_is_matched_by_name(self):
        supplier = Supplier.objects.create(name="loma")
        self.client.force_authenticate(self.admin)
        with patch("inventory.views.recognize_receipt", return_value=self._recognized()):
            response = self.client.post("/api/inventory/receipts/", {"image": png_upload()}, format="multipart")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["recognized"]["supplier"], supplier.pk)

    def test_rejects_other_extensions(self):
        self.client.force_authenticate(self.admin)
        upload = SimpleUploadedFile("receipt.txt", b"nope", content_type="text/plain")
        response = self.client.post("/api/inventory/receipts/", {"image": upload}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SupplyReceipt.objects.exists())

    def test_unknown_ingredient_fails_the_request(self):
        self.client.force_authenticate(self.admin)
        with patch("inventory.views.recognize_receipt", side_effect=ValueError("Unknown ingredient id 9.")):
            with self.assertRaises(ValueError):
                self.client.post("/api/inventory/receipts/", {"image": png_upload()}, format="multipart")
        self.assertFalse(SupplyReceipt.objects.exists())

    def test_requires_finance_admin(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post("/api/inventory/receipts/", {"image": png_upload()}, format="multipart")
        self.assertEqual(response.status_code, 403)

    def _supply_payload(self, receipts: list[int]) -> dict:
        return {
            "date": "2026-10-16",
            "supplier": None,
            "financial_transaction": None,
            "comment": "",
            "lines": [{"ingredient": self.menu.flour.pk, "quantity": "200", "total": "11.00"}],
            "receipts": receipts,
        }

    def test_saving_supply_links_and_unlinks_receipts(self):
        kept = SupplyReceipt.objects.create(image=receipt_image(), recognized={})
        dropped = SupplyReceipt.objects.create(image=receipt_image(), recognized={})
        self.client.force_authenticate(self.admin)
        created = self.client.post("/api/inventory/supplies/", self._supply_payload([kept.pk, dropped.pk]), format="json")
        self.assertEqual(created.status_code, 201, created.content)
        supply_id = created.json()["id"]
        self.assertEqual(
            created.json()["receipts"],
            [
                {"id": kept.pk, "image": f"/media/{kept.image.name}"},
                {"id": dropped.pk, "image": f"/media/{dropped.image.name}"},
            ],
        )
        kept.refresh_from_db()
        dropped.refresh_from_db()
        self.assertEqual(kept.supply_id, supply_id)
        self.assertEqual(dropped.supply_id, supply_id)

        other = Supply.objects.create(date="2026-10-01")
        foreign = SupplyReceipt.objects.create(supply=other, image=receipt_image(), recognized={})
        rejected = self.client.put(
            f"/api/inventory/supplies/{supply_id}/",
            self._supply_payload([kept.pk, foreign.pk]),
            format="json",
        )
        self.assertEqual(rejected.status_code, 400)

        updated = self.client.put(
            f"/api/inventory/supplies/{supply_id}/",
            self._supply_payload([kept.pk]),
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(updated.json()["receipts"], [{"id": kept.pk, "image": f"/media/{kept.image.name}"}])
        self.assertTrue(SupplyReceipt.objects.filter(pk=kept.pk, supply_id=supply_id).exists())
        self.assertFalse(SupplyReceipt.objects.filter(pk=dropped.pk).exists())
