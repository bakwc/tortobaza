import json
from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from menu.models import (
    Ingredient,
    Modifier,
    ModifierGroup,
    SemiProduct,
    SemiProductImage,
    SemiProductLine,
    TechCard,
    TechCardCategory,
    TechCardImage,
    TechCardLine,
    TechCardModifierGroup,
    TechCardModifierLine,
)

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "tech_cards.json"


class Command(BaseCommand):
    help = "Импортирует техкарты, полуфабрикаты и ингредиенты из JSON"

    def add_arguments(self, parser):
        parser.add_argument("--path", default=str(DATA_PATH))

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["path"])
        payload = json.loads(path.read_text())
        data_dir = path.resolve().parent
        categories = self._categories(payload["categories"])
        ingredients = self._ingredients(payload["ingredients"])
        semis = self._semis(payload["semi_products"])
        self._semi_lines(payload["semi_products"], semis, ingredients)
        self._cards(payload["tech_cards"], categories, semis, ingredients)
        modifiers = self._modifier_groups(payload["modifier_groups"])
        self._tech_card_modifiers(payload["tech_card_modifiers"], modifiers, semis, ingredients)
        self._images(payload["semi_products"], semis, SemiProductImage, "semi_product", data_dir)
        self._images(payload["tech_cards"], self._cards_by_name(payload["tech_cards"]), TechCardImage, "tech_card", data_dir)
        self.stdout.write(
            f"ingredients {len(ingredients)} semis {len(semis)} cards {len(payload['tech_cards'])}"
        )

    def _categories(self, rows: list[dict]) -> dict[str, TechCardCategory]:
        found = {}
        for row in rows:
            category, _created = TechCardCategory.objects.get_or_create(
                name=row["name"],
                defaults={"position": row["position"]},
            )
            found[category.name] = category
        return found

    def _ingredients(self, rows: list[dict]) -> dict[str, Ingredient]:
        found = {}
        for row in rows:
            ingredient, _created = Ingredient.objects.get_or_create(
                name=row["name"],
                defaults={"unit": row["unit"]},
            )
            if ingredient.unit != row["unit"]:
                raise CommandError(f"{ingredient.name}: unit {ingredient.unit} != {row['unit']}")
            found[ingredient.name] = ingredient
        return found

    def _semis(self, rows: list[dict]) -> dict[str, SemiProduct]:
        found = {}
        for row in rows:
            semi, _created = SemiProduct.objects.get_or_create(
                name=row["name"],
                defaults={
                    "unit": row["unit"],
                    "yield_quantity": Decimal(row["yield_quantity"]),
                    "is_produced": False,
                    "method": row["method"],
                },
            )
            semi.unit = row["unit"]
            semi.yield_quantity = Decimal(row["yield_quantity"])
            semi.is_produced = False
            semi.method = row["method"]
            semi.save()
            found[semi.name] = semi
        return found

    def _semi_lines(self, rows: list[dict], semis: dict[str, SemiProduct], ingredients: dict[str, Ingredient]) -> None:
        for row in rows:
            self._replace_lines(semis[row["name"]], SemiProductLine, "parent", row["lines"], ingredients, semis)

    def _cards(
        self,
        rows: list[dict],
        categories: dict[str, TechCardCategory],
        semis: dict[str, SemiProduct],
        ingredients: dict[str, Ingredient],
    ) -> None:
        for row in rows:
            basis = row["basis_weight_kg"]
            pieces = row["basis_quantity"]
            category_name = row["category"]
            card, _created = TechCard.objects.get_or_create(
                name=row["name"],
                defaults={
                    "kind": row["kind"],
                    "basis_weight_kg": None if basis is None else Decimal(basis),
                    "basis_quantity": None if pieces is None else int(pieces),
                    "method": row["method"],
                    "category": None if category_name is None else categories[category_name],
                },
            )
            card.kind = row["kind"]
            card.basis_weight_kg = None if basis is None else Decimal(basis)
            card.basis_quantity = None if pieces is None else int(pieces)
            card.method = row["method"]
            card.category = None if category_name is None else categories[category_name]
            card.save()
            self._replace_lines(card, TechCardLine, "tech_card", row["lines"], ingredients, semis)

    def _modifier_groups(self, rows: list[dict]) -> dict[tuple[str, str], Modifier]:
        found = {}
        for row in rows:
            group, _created = ModifierGroup.objects.get_or_create(
                name=row["name"],
                defaults={
                    "selection_type": row["selection_type"],
                    "is_required": row["is_required"],
                    "position": row["position"],
                },
            )
            group.selection_type = row["selection_type"]
            group.is_required = row["is_required"]
            group.position = row["position"]
            group.save()
            for position, name in enumerate(row["modifiers"]):
                modifier, _created = Modifier.objects.get_or_create(
                    group=group,
                    name=name,
                    defaults={"position": position},
                )
                modifier.position = position
                modifier.is_active = True
                modifier.save()
                found[(group.name, modifier.name)] = modifier
        return found

    def _tech_card_modifiers(
        self,
        rows: list[dict],
        modifiers: dict[tuple[str, str], Modifier],
        semis: dict[str, SemiProduct],
        ingredients: dict[str, Ingredient],
    ) -> None:
        for row in rows:
            card = TechCard.objects.get(name=row["tech_card"])
            group = ModifierGroup.objects.get(name=row["group"])
            TechCardModifierGroup.objects.update_or_create(
                tech_card=card,
                group=group,
                defaults={"position": row["position"]},
            )
            card.modifier_lines.filter(modifier__group=group).delete()
            for position, line in enumerate(row["lines"]):
                if "ingredient" in line:
                    component = {"ingredient": ingredients[line["ingredient"]], "semi_product": None}
                else:
                    component = {"ingredient": None, "semi_product": semis[line["semi_product"]]}
                TechCardModifierLine.objects.create(
                    tech_card=card,
                    modifier=modifiers[(group.name, line["modifier"])],
                    quantity=Decimal(line["quantity"]),
                    loss_percent=Decimal(line["loss_percent"]),
                    scales_by_weight=line["scales_by_weight"],
                    position=position,
                    **component,
                )

    def _cards_by_name(self, rows: list[dict]) -> dict[str, TechCard]:
        return {card.name: card for card in TechCard.objects.filter(name__in=[row["name"] for row in rows])}

    def _replace_lines(
        self,
        parent: SemiProduct | TechCard,
        line_model: type[SemiProductLine] | type[TechCardLine],
        parent_field: str,
        rows: list[dict],
        ingredients: dict[str, Ingredient],
        semis: dict[str, SemiProduct],
    ) -> None:
        parent.lines.all().delete()
        for position, row in enumerate(rows):
            if "ingredient" in row:
                component = {"ingredient": ingredients[row["ingredient"]], "semi_product": None}
            else:
                component = {"ingredient": None, "semi_product": semis[row["semi_product"]]}
            line_model.objects.create(
                **{parent_field: parent},
                quantity=Decimal(row["quantity"]),
                loss_percent=Decimal(row["loss_percent"]),
                position=position,
                **component,
            )

    def _images(
        self,
        rows: list[dict],
        parents: dict[str, SemiProduct] | dict[str, TechCard],
        image_model: type[SemiProductImage] | type[TechCardImage],
        parent_field: str,
        data_dir: Path,
    ) -> None:
        for row in rows:
            parent = parents[row["name"]]
            for image in list(parent.images.all()):
                image.image.delete(save=False)
                image.delete()
            for position, relative in enumerate(row["images"]):
                source = data_dir / relative
                with source.open("rb") as handle:
                    image = image_model(**{parent_field: parent, "position": position})
                    image.image.save(source.name, File(handle), save=True)
