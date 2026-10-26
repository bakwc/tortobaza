from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from menu.models import Modifier, TechCard
from menu.recipes import validate_order_item

_WEIGHT = Decimal("0.001")


def finished_signature(tech_card_id: int, weight_kg: Decimal | None, modifiers: list[tuple[int, int]]) -> str:
    if weight_kg is None:
        weight = ""
    else:
        weight = format(weight_kg.quantize(_WEIGHT), "f")
    pairs = ",".join(f"{modifier_id}:{quantity}" for modifier_id, quantity in sorted(modifiers))
    return f"{tech_card_id}|{weight}|{pairs}"


def stored_weight(tech_card: TechCard, weight_kg: Decimal | None) -> Decimal | None:
    if tech_card.kind == TechCard.KIND_PIECE:
        if weight_kg is not None:
            raise ValidationError(
                _("Piece tech card %(name)s cannot have a weight.") % {"name": tech_card.name}
            )
        return None
    if weight_kg is None or weight_kg <= 0:
        raise ValidationError(
            _("Tech card %(name)s is per kilogram, weight is required.") % {"name": tech_card.name}
        )
    return weight_kg.quantize(_WEIGHT)


def prepare_assembly(
    tech_card: TechCard,
    weight_kg: Decimal | None,
    modifiers: list[tuple[Modifier, int]],
) -> tuple[Decimal | None, str]:
    weight = stored_weight(tech_card, weight_kg)
    validate_order_item(tech_card, weight, modifiers)
    pairs = [(modifier.pk, quantity) for modifier, quantity in modifiers]
    return weight, finished_signature(tech_card.pk, weight, pairs)
