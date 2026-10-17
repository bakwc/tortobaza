from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from menu.models import Ingredient, TechCard, TechCardLine

CARD_NAME = "Опоссум с бататом"

INGREDIENTS = [
    ("Опоссум", "g"),
    ("Батат", "g"),
    ("Лук репчатый", "g"),
    ("Чеснок", "g"),
    ("Бульон", "g"),
    ("Яблочный уксус", "g"),
    ("Масло растительное", "g"),
    ("Соль", "g"),
    ("Перец чёрный", "g"),
    ("Паприка", "g"),
    ("Тимьян сухой", "g"),
    ("Горчица", "g"),
    ("Мёд", "g"),
]

LINES = [
    ("Опоссум", Decimal("1750")),
    ("Батат", Decimal("1200")),
    ("Лук репчатый", Decimal("300")),
    ("Чеснок", Decimal("20")),
    ("Бульон", Decimal("300")),
    ("Яблочный уксус", Decimal("30")),
    ("Масло растительное", Decimal("30")),
    ("Соль", Decimal("9")),
    ("Перец чёрный", Decimal("1")),
    ("Паприка", Decimal("2")),
    ("Тимьян сухой", Decimal("1")),
    ("Горчица", Decimal("15")),
    ("Мёд", Decimal("21")),
]

METHOD = """Выход: 4–6 порций. Подготовка около 30 минут, плюс маринование по желанию. Приготовление 2,5–3 часа. Состав на одну жаровню.

1. Используйте только мясо из проверенного источника. Удалите крупные видимые скопления жира и обсушите тушку бумажными полотенцами.
2. Смешайте уксус, масло, горчицу, соль, перец, паприку и тимьян. Натрите мясо и оставьте в холодильнике на 2–4 часа. Перед приготовлением снова обсушите.
3. Разогрейте духовку до 160°C. На сковороде быстро обжарьте куски со всех сторон до румяной корочки.
4. Батат нарежьте крупными дольками, лук — четвертинками. Выложите в жаровню, добавьте раздавленный чеснок и бульон.
5. Положите мясо поверх батата. Накройте крышкой или фольгой и готовьте около 2 часов. Снимите крышку и запекайте ещё 20–30 минут, чтобы мясо и батат подрумянились. Если жидкость выкипает, подлейте воду или бульон.
6. Измерьте температуру в самой толстой части, не касаясь кости: не ниже 71°C. Доведите мясо до мягкости и проверьте вилкой.
7. Дайте постоять 10 минут. Подавайте с бататом и соком из жаровни.

## Примечания

- Опоссум: в карточке 1,5–2 кг, в составе 1750 г. Подготовленная тушка, разделанная на крупные части.
- Лук репчатый: 2 шт, 1 шт = 150 г
- Чеснок: 4 зубчика, 1 зубчик = 5 г
- Бульон: 300 мл. Можно заменить водой.
- Яблочный уксус: 2 ст. л., 1 ст. л. = 15 г
- Масло растительное: 2 ст. л., 1 ст. л. = 15 г
- Соль: 1½ ч. л. или по вкусу, 1 ч. л. = 6 г
- Перец чёрный: ½ ч. л., в составе 1 г
- Паприка: 1 ч. л., в составе 2 г
- Тимьян сухой: 1 ч. л., в составе 1 г
- Горчица: 1 ст. л., в составе 15 г
- Мёд: 1 ст. л. по желанию, в составе 21 г. Можно заменить кленовым сиропом.
- Не используйте сбитого на дороге зверя. При разделке соблюдайте чистоту и не допускайте контакта сырого мяса с готовой едой.
- Без опоссума подойдут кролик или свиная лопатка; время приготовления нужно скорректировать.
"""


class Command(BaseCommand):
    help = "Создаёт или обновляет техкарту «Опоссум с бататом» и её ингредиенты"

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
        card, _created = TechCard.objects.get_or_create(
            name=CARD_NAME,
            defaults={
                "kind": TechCard.KIND_PIECE,
                "basis_quantity": 1,
                "method": METHOD,
            },
        )
        card.kind = TechCard.KIND_PIECE
        card.basis_weight_kg = None
        card.basis_quantity = 1
        card.method = METHOD
        card.is_active = True
        card.save()
        card.sections.all().delete()
        card.lines.all().delete()
        for position, (name, quantity) in enumerate(LINES):
            TechCardLine.objects.create(
                tech_card=card,
                ingredient=ingredients[name],
                semi_product=None,
                quantity=quantity,
                loss_percent=Decimal("0"),
                position=position,
            )
        self.stdout.write(f"{card.name}: lines {len(LINES)}")
