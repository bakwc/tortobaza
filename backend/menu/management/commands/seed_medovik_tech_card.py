from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from menu.models import Ingredient, TechCard, TechCardCategory, TechCardLine, TechCardSection

CARD_NAME = "Медовик весовой"

CATEGORY_NAME = "Торты"

INGREDIENTS = [
    ("Мёд", "g"),
    ("Сахар", "g"),
    ("Соль", "g"),
    ("Масло сливочное", "g"),
    ("Яйцо", "g"),
    ("Мука пшеничная", "g"),
    ("Сода", "g"),
    ("Сметана", "g"),
    ("Сыр творожный", "g"),
    ("Сливки 33%", "g"),
    ("Сахарная пудра", "g"),
]

SECTIONS = [
    (
        "Медовые коржи",
        """1. Карамелизовать мёд и сахар.
2. Ввести масло и соль.
3. Остудить до 45°C.
4. Добавить яйца.
5. Ввести муку и соду.
6. Стабилизировать тесто 5 часов.
7. Выпекать коржи при 160°C 5–8 минут.""",
        [
            ("Мёд", Decimal("85")),
            ("Сахар", Decimal("68")),
            ("Соль", Decimal("0.5")),
            ("Масло сливочное", Decimal("64")),
            ("Яйцо", Decimal("55")),
            ("Мука пшеничная", Decimal("205")),
            ("Сода", Decimal("2.3")),
        ],
    ),
    (
        "Сметанный крем",
        "1. Взбить крем.",
        [
            ("Сметана", Decimal("259")),
            ("Сыр творожный", Decimal("166")),
            ("Сливки 33%", Decimal("55")),
            ("Мёд", Decimal("15")),
            ("Сахарная пудра", Decimal("55")),
        ],
    ),
]

METHOD = """Медовый торт на карамелизированном гречишном мёде со сметанно-сырным кремом.

1. Собрать торт.
2. Стабилизировать 8–9 часов.

## Размеры

- 1 кг — диаметр 16 см
- 1,5 кг — диаметр 16 см, высокий
- 2 кг — диаметр 18 см
- 2,5 кг — диаметр 18 см, высокий
- 3 кг — диаметр 20 см

## Хранение

Готовое изделие: 72 часа при +2...+6°C

## Контроль качества

- Вес соответствует ТК
- Срез ровный
- Упакован
"""


class Command(BaseCommand):
    help = "Создаёт или обновляет весовую техкарту «Медовик весовой» и её ингредиенты"

    @transaction.atomic
    def handle(self, *args, **options):
        ingredients = {}
        for name, unit in INGREDIENTS:
            ingredient, _created = Ingredient.objects.get_or_create(
                name=name,
                defaults={"unit": unit},
            )
            if ingredient.unit != unit:
                raise CommandError(f"{ingredient.name}: unit {ingredient.unit} != {unit}")
            ingredients[name] = ingredient
        category = TechCardCategory.objects.get(name=CATEGORY_NAME)
        card, _created = TechCard.objects.get_or_create(
            name=CARD_NAME,
            defaults={
                "kind": TechCard.KIND_WEIGHTED,
                "basis_weight_kg": Decimal("1"),
                "method": METHOD,
                "category": category,
            },
        )
        card.kind = TechCard.KIND_WEIGHTED
        card.basis_weight_kg = Decimal("1")
        card.basis_quantity = None
        card.method = METHOD
        card.category = category
        card.is_active = True
        card.save()
        card.lines.all().delete()
        card.sections.all().delete()
        lines_count = 0
        for position, (section_name, section_method, lines) in enumerate(SECTIONS):
            section = TechCardSection.objects.create(
                tech_card=card,
                name=section_name,
                method=section_method,
                position=position,
            )
            for line_position, (name, quantity) in enumerate(lines):
                TechCardLine.objects.create(
                    tech_card=card,
                    section=section,
                    ingredient=ingredients[name],
                    semi_product=None,
                    quantity=quantity,
                    quantity_unit=ingredients[name].unit,
                    loss_percent=Decimal("0"),
                    position=line_position,
                )
                lines_count += 1
        self.stdout.write(f"{card.name}: sections {len(SECTIONS)} lines {lines_count}")
