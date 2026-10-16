from datetime import date
from decimal import Decimal

from crm.models import CrmOrder, CrmOrderItem, CrmOrderItemModifier
from menu.models import (
    UNIT_GRAM,
    UNIT_MILLILITER,
    UNIT_PIECE,
    Ingredient,
    Modifier,
    ModifierGroup,
    SemiProduct,
    SemiProductLine,
    TechCard,
    TechCardLine,
    TechCardModifierGroup,
    TechCardModifierLine,
)


class MenuFixture:
    def __init__(self):
        self.flour = Ingredient.objects.create(name="Flour", unit=UNIT_GRAM, avg_cost=Decimal("0.01"))
        self.sugar = Ingredient.objects.create(name="Sugar", unit=UNIT_GRAM, avg_cost=Decimal("0.005"))
        self.cream = Ingredient.objects.create(name="Cream", unit=UNIT_MILLILITER, avg_cost=Decimal("0.02"))
        self.raspberry = Ingredient.objects.create(name="Raspberry", unit=UNIT_GRAM, avg_cost=Decimal("0.03"))
        self.paper = Ingredient.objects.create(name="Photo paper", unit=UNIT_PIECE, avg_cost=Decimal("1.5"))
        self.ink = Ingredient.objects.create(name="Food ink", unit=UNIT_MILLILITER, avg_cost=Decimal("0.1"))

        self.sponge = SemiProduct.objects.create(
            name="Sponge",
            unit=UNIT_GRAM,
            yield_quantity=Decimal("1000"),
            is_produced=False,
        )
        SemiProductLine.objects.create(parent=self.sponge, ingredient=self.flour, quantity=Decimal("600"))
        SemiProductLine.objects.create(parent=self.sponge, ingredient=self.sugar, quantity=Decimal("400"))

        self.frozen_sponge = SemiProduct.objects.create(
            name="Frozen sponge",
            unit=UNIT_GRAM,
            yield_quantity=Decimal("1000"),
            is_produced=True,
        )
        SemiProductLine.objects.create(parent=self.frozen_sponge, ingredient=self.flour, quantity=Decimal("600"))
        SemiProductLine.objects.create(parent=self.frozen_sponge, ingredient=self.sugar, quantity=Decimal("400"))

        self.filling = ModifierGroup.objects.create(
            name="Filling",
            selection_type=ModifierGroup.SELECTION_SINGLE,
            is_required=True,
        )
        self.raspberry_filling = Modifier.objects.create(group=self.filling, name="Raspberry")
        self.mango_filling = Modifier.objects.create(group=self.filling, name="Mango")
        self.decor = ModifierGroup.objects.create(
            name="Decor",
            selection_type=ModifierGroup.SELECTION_MULTI,
            is_required=False,
        )
        self.photo = Modifier.objects.create(group=self.decor, name="Photo print")
        self.berries = Modifier.objects.create(group=self.decor, name="Berries")
        self.extras = ModifierGroup.objects.create(name="Extras", selection_type=ModifierGroup.SELECTION_MULTI)
        self.balloon = Modifier.objects.create(group=self.extras, name="Balloon")

        self.cake = TechCard.objects.create(
            name="Cake",
            kind=TechCard.KIND_WEIGHTED,
            basis_weight_kg=Decimal("1"),
        )
        TechCardLine.objects.create(tech_card=self.cake, semi_product=self.sponge, quantity=Decimal("500"))
        TechCardLine.objects.create(tech_card=self.cake, ingredient=self.cream, quantity=Decimal("300"))
        TechCardModifierGroup.objects.create(tech_card=self.cake, group=self.filling, position=0)
        TechCardModifierGroup.objects.create(tech_card=self.cake, group=self.decor, position=1)
        TechCardModifierLine.objects.create(
            tech_card=self.cake,
            modifier=self.raspberry_filling,
            ingredient=self.raspberry,
            quantity=Decimal("100"),
            scales_by_weight=True,
        )
        TechCardModifierLine.objects.create(
            tech_card=self.cake,
            modifier=self.photo,
            ingredient=self.paper,
            quantity=Decimal("1"),
            scales_by_weight=False,
        )
        TechCardModifierLine.objects.create(
            tech_card=self.cake,
            modifier=self.photo,
            ingredient=self.ink,
            quantity=Decimal("2"),
            scales_by_weight=False,
        )
        TechCardModifierLine.objects.create(
            tech_card=self.cake,
            modifier=self.berries,
            ingredient=self.raspberry,
            quantity=Decimal("50"),
            scales_by_weight=True,
        )

        self.bento = TechCard.objects.create(name="Bento", kind=TechCard.KIND_PIECE, basis_quantity=1)
        TechCardLine.objects.create(tech_card=self.bento, ingredient=self.flour, quantity=Decimal("100"))

        self.frozen_cake = TechCard.objects.create(
            name="Frozen cake",
            kind=TechCard.KIND_PIECE,
            basis_quantity=1,
        )
        TechCardLine.objects.create(tech_card=self.frozen_cake, semi_product=self.frozen_sponge, quantity=Decimal("400"))


def make_crm_order(status: str) -> CrmOrder:
    return CrmOrder.objects.create(
        date=date(2026, 10, 20),
        contact="Anna",
        weight="1 kg",
        filling="Raspberry",
        cake_price=Decimal("100.00"),
        status=status,
    )


def add_item(
    order: CrmOrder,
    tech_card: TechCard | None,
    weight_kg: Decimal | None,
    quantity: int,
    modifiers: list[tuple[Modifier, int]],
) -> CrmOrderItem:
    item = CrmOrderItem.objects.create(
        order=order,
        tech_card=tech_card,
        name="",
        quantity=quantity,
        weight_kg=weight_kg,
    )
    for modifier, modifier_quantity in modifiers:
        CrmOrderItemModifier.objects.create(item=item, modifier=modifier, quantity=modifier_quantity)
    return item
