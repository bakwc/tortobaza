import json
import tempfile
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from PIL import Image

from menu.models import Ingredient, SemiProduct, TechCard


class ImportTechCardsTests(TestCase):
    def test_imports_ingredient_semi_and_weighted_card(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = root / "images"
            images.mkdir()
            png = images / "card.png"
            Image.new("RGB", (1, 1), (10, 20, 30)).save(png, "PNG")
            payload = {
                "categories": [{"name": "Торты", "position": 0}],
                "ingredients": [{"name": "Мука", "unit": "g"}],
                "semi_products": [
                    {
                        "name": "Бисквит",
                        "unit": "g",
                        "yield_quantity": "100",
                        "method": "Взбить.",
                        "images": [],
                        "lines": [{"ingredient": "Мука", "quantity": "100", "loss_percent": "0"}],
                    }
                ],
                "tech_cards": [
                    {
                        "name": "Торт",
                        "kind": "weighted",
                        "basis_weight_kg": "1.5",
                        "basis_quantity": None,
                        "category": "Торты",
                        "method": "## Сборка\n\n1. Собрать слои.",
                        "images": ["images/card.png"],
                        "lines": [{"semi_product": "Бисквит", "quantity": "500", "loss_percent": "0"}],
                    }
                ],
            }
            path = root / "cards.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            TechCard.objects.create(name="Не трогать", kind=TechCard.KIND_PIECE, method="stay")
            call_command("import_tech_cards", path=str(path))
            card = TechCard.objects.get(name="Торт")
            self.assertEqual(card.basis_weight_kg, Decimal("1.5"))
            self.assertIsNone(card.basis_quantity)
            self.assertEqual(card.method, "## Сборка\n\n1. Собрать слои.")
            self.assertEqual(card.lines.get().semi_product.name, "Бисквит")
            self.assertEqual(card.lines.get().quantity, Decimal("500"))
            self.assertEqual(card.images.count(), 1)
            semi = SemiProduct.objects.get(name="Бисквит")
            self.assertEqual(semi.method, "Взбить.")
            self.assertEqual(semi.lines.get().ingredient, Ingredient.objects.get(name="Мука"))
            self.assertEqual(TechCard.objects.get(name="Не трогать").method, "stay")
            payload["tech_cards"][0]["method"] = "### Крем\n\n- Обновить."
            payload["tech_cards"][0]["lines"][0]["quantity"] = "250"
            path.write_text(json.dumps(payload), encoding="utf-8")
            call_command("import_tech_cards", path=str(path))
            card.refresh_from_db()
            self.assertEqual(card.method, "### Крем\n\n- Обновить.")
            self.assertEqual(card.lines.get().quantity, Decimal("250"))
            self.assertEqual(card.images.count(), 1)
            self.assertEqual(TechCard.objects.filter(name="Торт").count(), 1)
            self.assertTrue(TechCard.objects.filter(name="Не трогать").exists())
