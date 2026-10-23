from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from menu.models import (
    UNIT_GRAM,
    Ingredient,
    Modifier,
    ModifierGroup,
    SemiProduct,
    TechCard,
)

Component = Ingredient | SemiProduct
Needs = dict[Component, Decimal]

_HUNDRED = Decimal("100")
_ONE = Decimal("1")
_CENT = Decimal("0.01")


def gross_quantity(quantity: Decimal, loss_percent: Decimal) -> Decimal:
    return quantity * _HUNDRED / (_HUNDRED - loss_percent)


def component_quantity(component: Component, quantity: Decimal, quantity_unit: str) -> Decimal:
    if quantity_unit == component.unit:
        return quantity
    if quantity_unit == UNIT_GRAM and isinstance(component, Ingredient) and component.unit != UNIT_GRAM:
        if component.grams_per_unit is None:
            raise ValidationError(
                _("Ingredient %(name)s has no grams per unit.") % {"name": component.name}
            )
        return quantity / component.grams_per_unit
    raise ValidationError(
        _("Quantity unit %(quantity_unit)s cannot be converted to %(unit)s for %(name)s.")
        % {"quantity_unit": quantity_unit, "unit": component.unit, "name": component.name}
    )


def line_component_quantity(line) -> Decimal:
    return component_quantity(
        line.component,
        gross_quantity(line.quantity, line.loss_percent),
        line.quantity_unit,
    )


def _add(needs: Needs, component: Component, quantity: Decimal) -> None:
    needs[component] = needs.get(component, Decimal("0")) + quantity


def _merge(target: Needs, source: Needs) -> None:
    for component, quantity in source.items():
        _add(target, component, quantity)


def _semi_lines(semi_product: SemiProduct):
    return semi_product.lines.select_related("ingredient", "semi_product")


def _explode(component: Component, quantity: Decimal, needs: Needs, path: frozenset[int]) -> None:
    if isinstance(component, Ingredient) or component.is_produced:
        _add(needs, component, quantity)
        return
    if component.pk in path:
        raise ValidationError(_("Semi-product %(name)s contains itself.") % {"name": component.name})
    factor = quantity / component.yield_quantity
    nested_path = path | {component.pk}
    for line in _semi_lines(component):
        _explode(
            line.component,
            line_component_quantity(line) * factor,
            needs,
            nested_path,
        )


def expand_component(component: Component, quantity: Decimal) -> Needs:
    needs: Needs = {}
    _explode(component, quantity, needs, frozenset())
    return needs


def expand_semi_product(semi_product: SemiProduct, quantity: Decimal) -> Needs:
    needs: Needs = {}
    factor = quantity / semi_product.yield_quantity
    path = frozenset({semi_product.pk})
    for line in _semi_lines(semi_product):
        _explode(
            line.component,
            line_component_quantity(line) * factor,
            needs,
            path,
        )
    return needs


def _min_selections(group: ModifierGroup, required: bool) -> int:
    if group.selection_type == ModifierGroup.SELECTION_SINGLE:
        return 1 if required else 0
    if required and group.min_selections < 1:
        return 1
    return group.min_selections


def _max_selections(group: ModifierGroup) -> int | None:
    if group.selection_type == ModifierGroup.SELECTION_SINGLE:
        return 1
    return group.max_selections


def order_item_errors(
    tech_card: TechCard | None,
    weight_kg: Decimal | None,
    modifiers: list[tuple[Modifier, int]],
) -> list[str]:
    errors: list[str] = []
    if tech_card is None:
        if modifiers:
            errors.append(_("An item without a tech card cannot have modifiers."))
        return errors
    if tech_card.kind == TechCard.KIND_WEIGHTED and (weight_kg is None or weight_kg <= 0):
        errors.append(
            _("Tech card %(name)s is per kilogram, weight is required.") % {"name": tech_card.name}
        )
    links = {link.group_id: link for link in tech_card.modifier_groups.select_related("group")}
    counts: dict[int, int] = defaultdict(int)
    seen: set[int] = set()
    for modifier, quantity in modifiers:
        if quantity < 1:
            errors.append(_("Modifier quantity must be at least 1."))
        if modifier.pk in seen:
            errors.append(_("Modifier %(name)s is selected twice.") % {"name": modifier.name})
        seen.add(modifier.pk)
        if modifier.group_id not in links:
            errors.append(
                _("Modifier %(name)s is not available for tech card %(card)s.")
                % {"name": modifier.name, "card": tech_card.name}
            )
        counts[modifier.group_id] += 1
    for link in links.values():
        group = link.group
        selected = counts[group.pk]
        minimum = _min_selections(group, link.effective_is_required)
        maximum = _max_selections(group)
        if selected < minimum:
            errors.append(
                _("Choose at least %(count)s in group %(group)s.")
                % {"count": minimum, "group": group.name}
            )
        if maximum is not None and selected > maximum:
            errors.append(
                _("Choose at most %(count)s in group %(group)s.")
                % {"count": maximum, "group": group.name}
            )
    return errors


def validate_order_item(
    tech_card: TechCard | None,
    weight_kg: Decimal | None,
    modifiers: list[tuple[Modifier, int]],
) -> None:
    errors = order_item_errors(tech_card, weight_kg, modifiers)
    if errors:
        raise ValidationError(errors)


def expand_order_item(
    tech_card: TechCard | None,
    weight_kg: Decimal | None,
    quantity: int,
    modifiers: list[tuple[Modifier, int]],
    lines: list[tuple[Component, Decimal]],
) -> Needs:
    needs: Needs = {}
    item_quantity = Decimal(quantity)
    if tech_card is not None:
        if tech_card.kind == TechCard.KIND_WEIGHTED:
            weight_factor = weight_kg / tech_card.basis_weight_kg
            line_factor = weight_factor * item_quantity
        else:
            weight_factor = _ONE
            line_factor = item_quantity / Decimal(tech_card.basis_quantity)
        for line in tech_card.lines.select_related("ingredient", "semi_product"):
            _explode(
                line.component,
                line_component_quantity(line) * line_factor,
                needs,
                frozenset(),
            )
        by_modifier = defaultdict(list)
        for line in tech_card.modifier_lines.select_related("ingredient", "semi_product"):
            by_modifier[line.modifier_id].append(line)
        for modifier, modifier_quantity in modifiers:
            for line in by_modifier[modifier.pk]:
                factor = Decimal(modifier_quantity) * item_quantity
                if line.scales_by_weight:
                    factor = factor * weight_factor
                _explode(
                    line.component,
                    line_component_quantity(line) * factor,
                    needs,
                    frozenset(),
                )
    for component, line_quantity in lines:
        _explode(component, line_quantity, needs, frozenset())
    return needs


def expand_order(crm_order) -> Needs:
    needs: Needs = {}
    items = crm_order.items.select_related("tech_card").prefetch_related(
        "modifiers__modifier",
        "lines__ingredient",
        "lines__semi_product",
    )
    for item in items:
        _merge(
            needs,
            expand_order_item(
                item.tech_card,
                item.weight_kg,
                item.quantity,
                [(row.modifier, row.quantity) for row in item.modifiers.all()],
                [(row.component, row.quantity) for row in item.lines.all()],
            ),
        )
    return needs


def needs_cost(needs: Needs) -> Decimal:
    total = Decimal("0")
    for component, quantity in needs.items():
        total += quantity * component.avg_cost
    return total.quantize(_CENT)


def tech_card_cost(
    tech_card: TechCard,
    modifiers: list[tuple[Modifier, int]],
    weight_kg: Decimal | None,
) -> Decimal:
    count = 1 if tech_card.kind == TechCard.KIND_WEIGHTED else tech_card.basis_quantity
    return needs_cost(expand_order_item(tech_card, weight_kg, count, modifiers, []))


def order_cost(crm_order) -> Decimal:
    return needs_cost(expand_order(crm_order))


def missing_modifier_compositions(tech_card: TechCard) -> list[Modifier]:
    filled = set(tech_card.modifier_lines.values_list("modifier_id", flat=True))
    group_ids = tech_card.modifier_groups.values_list("group_id", flat=True)
    return list(
        Modifier.objects.filter(group_id__in=group_ids, is_active=True)
        .exclude(pk__in=filled)
        .select_related("group")
    )
