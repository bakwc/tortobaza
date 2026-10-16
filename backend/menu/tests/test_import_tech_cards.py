import json
import tempfile
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from PIL import Image

from menu.models import Ingredient, Modifier, ModifierGroup, SemiProduct, TechCard, TechCardSection


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
                        "sections": [
                            {
                                "name": "Пропитка",
                                "method": "Смешать.",
                                "lines": [{"ingredient": "Мука", "quantity": "200", "loss_percent": "0"}],
                            },
                            {"name": "Сборка", "method": "Собрать слои.", "lines": []},
                        ],
                    }
                ],
                "modifier_groups": [
                    {
                        "name": "Основа",
                        "selection_type": "single",
                        "is_required": True,
                        "position": 0,
                        "modifiers": [{"name": "Бисквит", "semi_product": "Бисквит"}],
                    }
                ],
                "tech_card_modifiers": [
                    {
                        "tech_card": "Торт",
                        "group": "Основа",
                        "position": 0,
                        "lines": [
                            {
                                "modifier": "Бисквит",
                                "semi_product": "Бисквит",
                                "quantity": "300",
                                "loss_percent": "0",
                                "scales_by_weight": True,
                            }
                        ],
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
            loose = card.lines.get(section__isnull=True)
            self.assertEqual(loose.semi_product.name, "Бисквит")
            self.assertEqual(loose.quantity, Decimal("500"))
            syrup = card.sections.get(name="Пропитка")
            self.assertEqual(syrup.method, "Смешать.")
            self.assertEqual(syrup.position, 0)
            syrup_line = syrup.lines.get()
            self.assertEqual(syrup_line.ingredient, Ingredient.objects.get(name="Мука"))
            self.assertEqual(syrup_line.quantity, Decimal("200"))
            self.assertEqual(syrup_line.tech_card, card)
            assembly = card.sections.get(name="Сборка")
            self.assertEqual(assembly.method, "Собрать слои.")
            self.assertEqual(assembly.lines.count(), 0)
            self.assertEqual(card.images.count(), 1)
            self.assertEqual(card.modifier_groups.get().group, ModifierGroup.objects.get(name="Основа"))
            modifier_line = card.modifier_lines.get()
            modifier = Modifier.objects.get(group__name="Основа", name="Бисквит")
            self.assertEqual(modifier_line.modifier, modifier)
            self.assertEqual(modifier.semi_product.name, "Бисквит")
            self.assertIsNone(modifier.ingredient)
            self.assertEqual(modifier_line.semi_product.name, "Бисквит")
            self.assertEqual(modifier_line.quantity, Decimal("300"))
            semi = SemiProduct.objects.get(name="Бисквит")
            self.assertEqual(semi.method, "Взбить.")
            self.assertEqual(semi.lines.get().ingredient, Ingredient.objects.get(name="Мука"))
            self.assertEqual(TechCard.objects.get(name="Не трогать").method, "stay")
            payload["tech_cards"][0]["method"] = "### Крем\n\n- Обновить."
            payload["tech_cards"][0]["lines"][0]["quantity"] = "250"
            payload["tech_cards"][0]["sections"] = [
                {
                    "name": "Крем",
                    "method": "Взбить.",
                    "lines": [{"semi_product": "Бисквит", "quantity": "40", "loss_percent": "0"}],
                }
            ]
            path.write_text(json.dumps(payload), encoding="utf-8")
            call_command("import_tech_cards", path=str(path))
            card.refresh_from_db()
            self.assertEqual(card.method, "### Крем\n\n- Обновить.")
            self.assertEqual(card.lines.get(section__isnull=True).quantity, Decimal("250"))
            self.assertEqual(list(card.sections.values_list("name", flat=True)), ["Крем"])
            cream = TechCardSection.objects.get(tech_card=card, name="Крем")
            self.assertEqual(cream.lines.get().semi_product.name, "Бисквит")
            self.assertEqual(cream.lines.get().quantity, Decimal("40"))
            self.assertEqual(card.images.count(), 1)
            self.assertEqual(card.modifier_lines.count(), 1)
            self.assertEqual(TechCard.objects.filter(name="Торт").count(), 1)
            self.assertTrue(TechCard.objects.filter(name="Не трогать").exists())
