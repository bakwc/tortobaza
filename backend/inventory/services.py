from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext as _

from crm.models import CrmOrder
from inventory.finished import finished_signature, prepare_assembly
from inventory.models import (
    FinishedGood,
    FinishedGoodModifier,
    FinishedProduction,
    FinishedProductionLine,
    InventoryCount,
    InventoryCountLine,
    Production,
    StockMovement,
    Supply,
    WriteOff,
    WriteOffLine,
)
from menu.models import Ingredient, Modifier, SemiProduct, TechCard
from menu.recipes import Component, Needs, expand_component, expand_order_item, expand_semi_product

StockItem = Ingredient | SemiProduct | FinishedGood

WRITE_OFF_STATUSES = frozenset(
    {
        CrmOrder.STATUS_READY,
        CrmOrder.STATUS_CLIENT_APPROVED,
        CrmOrder.STATUS_IN_DELIVERY,
        CrmOrder.STATUS_DELIVERED,
    }
)

_ZERO = Decimal("0")
_COST_PLACES = Decimal("0.000001")
_QUANTITY_PLACES = Decimal("0.0001")


def _key(
    ingredient_id: int | None,
    semi_product_id: int | None,
    finished_good_id: int | None,
) -> tuple[str, int]:
    if ingredient_id is not None:
        return ("ingredient", ingredient_id)
    if semi_product_id is not None:
        return ("semi_product", semi_product_id)
    return ("finished_good", finished_good_id)


def _component_key(component: StockItem) -> tuple[str, int]:
    if isinstance(component, Ingredient):
        return ("ingredient", component.pk)
    if isinstance(component, SemiProduct):
        return ("semi_product", component.pk)
    return ("finished_good", component.pk)


def _component_fields(component: StockItem) -> dict:
    if isinstance(component, Ingredient):
        return {"ingredient": component, "semi_product": None, "finished_good": None}
    if isinstance(component, SemiProduct):
        return {"ingredient": None, "semi_product": component, "finished_good": None}
    return {"ingredient": None, "semi_product": None, "finished_good": component}


def _production_cost_key(movement: StockMovement) -> tuple[str, int] | None:
    if movement.finished_production_line_id is not None:
        return ("finished", movement.finished_production_line_id)
    if movement.production_id is not None:
        return ("semi", movement.production_id)
    return None


def _require_whole_pieces(quantity: Decimal, allow_zero: bool) -> None:
    if quantity != quantity.to_integral_value() or quantity < 0 or (not allow_zero and quantity <= 0):
        raise ValidationError(_("Finished good quantity must be a whole number of pieces."))


def _quantize_quantity(value: Decimal) -> Decimal:
    return value.quantize(_QUANTITY_PLACES)


def _quantize_cost(value: Decimal) -> Decimal:
    return value.quantize(_COST_PLACES)


def is_stocked(component: StockItem) -> bool:
    if isinstance(component, FinishedGood):
        return True
    return isinstance(component, Ingredient) or component.is_produced


def _stored_costs() -> dict[tuple[str, int], Decimal]:
    costs = {("ingredient", pk): cost for pk, cost in Ingredient.objects.values_list("pk", "avg_cost")}
    costs.update({("semi_product", pk): cost for pk, cost in SemiProduct.objects.values_list("pk", "avg_cost")})
    costs.update({("finished_good", pk): cost for pk, cost in FinishedGood.objects.values_list("pk", "avg_cost")})
    return costs


def recompute_costs() -> None:
    stored_costs = _stored_costs()
    quantities: dict[tuple[str, int], Decimal] = {}
    averages: dict[tuple[str, int], Decimal] = {}
    production_costs: dict[tuple[str, int], Decimal] = {}
    changed: list[StockMovement] = []
    for movement in StockMovement.objects.select_related("inventory_count_line").order_by("date", "id"):
        key = _key(movement.ingredient_id, movement.semi_product_id, movement.finished_good_id)
        quantity = quantities.get(key, _ZERO)
        average = averages[key] if key in averages else stored_costs[key]
        cost_key = _production_cost_key(movement)
        if movement.kind == StockMovement.KIND_SUPPLY:
            incoming_cost = movement.unit_cost
        elif movement.kind == StockMovement.KIND_PRODUCTION_IN:
            incoming_cost = _quantize_cost(production_costs.get(cost_key, _ZERO) / movement.quantity)
        elif movement.kind == StockMovement.KIND_INVENTORY and movement.quantity > 0:
            incoming_cost = movement.inventory_count_line.unit_cost
        else:
            incoming_cost = None
        if incoming_cost is not None or (movement.kind == StockMovement.KIND_INVENTORY and movement.quantity > 0):
            unit_cost = average if incoming_cost is None else incoming_cost
            if quantity <= 0:
                average = unit_cost
            else:
                average = _quantize_cost(
                    (quantity * average + movement.quantity * unit_cost) / (quantity + movement.quantity)
                )
        else:
            unit_cost = average
            if movement.kind == StockMovement.KIND_PRODUCTION_OUT:
                production_costs[cost_key] = (
                    production_costs.get(cost_key, _ZERO) - movement.quantity * unit_cost
                )
        if movement.unit_cost != unit_cost:
            movement.unit_cost = unit_cost
            changed.append(movement)
        quantities[key] = quantity + movement.quantity
        averages[key] = average
    StockMovement.objects.bulk_update(changed, ["unit_cost"])
    ingredient_ids = [pk for kind, pk in averages if kind == "ingredient"]
    for ingredient in Ingredient.objects.filter(pk__in=ingredient_ids):
        value = averages[("ingredient", ingredient.pk)]
        if ingredient.avg_cost != value:
            ingredient.avg_cost = value
            ingredient.save(update_fields=["avg_cost"])
    semi_product_ids = [pk for kind, pk in averages if kind == "semi_product"]
    for semi_product in SemiProduct.objects.filter(pk__in=semi_product_ids):
        value = averages[("semi_product", semi_product.pk)]
        if semi_product.avg_cost != value:
            semi_product.avg_cost = value
            semi_product.save(update_fields=["avg_cost"])
    finished_good_ids = [pk for kind, pk in averages if kind == "finished_good"]
    for finished_good in FinishedGood.objects.filter(pk__in=finished_good_ids):
        value = averages[("finished_good", finished_good.pk)]
        if finished_good.avg_cost != value:
            finished_good.avg_cost = value
            finished_good.save(update_fields=["avg_cost"])


def stock_levels(on_date: date | None, exclude_count: InventoryCount | None) -> dict[tuple[str, int], Decimal]:
    movements = StockMovement.objects.all()
    if on_date is not None:
        movements = movements.filter(date__lte=on_date)
    if exclude_count is not None:
        movements = movements.exclude(inventory_count_line__count=exclude_count)
    rows = movements.values("ingredient_id", "semi_product_id", "finished_good_id").annotate(total=Sum("quantity"))
    return {
        _key(row["ingredient_id"], row["semi_product_id"], row["finished_good_id"]): row["total"] for row in rows
    }


def stock_of(component: StockItem, levels: dict[tuple[str, int], Decimal]) -> Decimal:
    return levels.get(_component_key(component), _ZERO)


def _merge(target: Needs, source: Needs) -> None:
    for component, quantity in source.items():
        target[component] = target.get(component, Decimal("0")) + quantity


def _create_outgoing(needs: Needs, movement_date: date, kind: str, link: dict) -> None:
    for component, quantity in needs.items():
        StockMovement.objects.create(
            date=movement_date,
            kind=kind,
            quantity=_quantize_quantity(-quantity),
            unit_cost=component.avg_cost,
            **_component_fields(component),
            **link,
        )


def _create_finished_outgoing(
    quantities: dict[FinishedGood, Decimal],
    movement_date: date,
    kind: str,
    link: dict,
) -> None:
    for good, quantity in quantities.items():
        StockMovement.objects.create(
            date=movement_date,
            kind=kind,
            quantity=_quantize_quantity(-quantity),
            unit_cost=good.avg_cost,
            finished_good=good,
            **link,
        )


def ensure_finished_good(
    tech_card: TechCard,
    weight_kg: Decimal | None,
    modifiers: list[tuple[Modifier, int]],
) -> FinishedGood:
    weight, signature = prepare_assembly(tech_card, weight_kg, modifiers)
    good = FinishedGood.objects.filter(signature=signature).first()
    if good is not None:
        return good
    good = FinishedGood.objects.create(tech_card=tech_card, weight_kg=weight, signature=signature)
    for modifier, quantity in modifiers:
        FinishedGoodModifier.objects.create(finished_good=good, modifier=modifier, quantity=quantity)
    return good


def drop_orphan_finished_goods() -> None:
    used: set[int] = set()
    used.update(FinishedProductionLine.objects.values_list("finished_good_id", flat=True))
    used.update(WriteOffLine.objects.exclude(finished_good_id=None).values_list("finished_good_id", flat=True))
    used.update(
        InventoryCountLine.objects.exclude(finished_good_id=None).values_list("finished_good_id", flat=True)
    )
    used.update(StockMovement.objects.exclude(finished_good_id=None).values_list("finished_good_id", flat=True))
    FinishedGood.objects.exclude(pk__in=used).delete()


@transaction.atomic
def apply_supply(supply: Supply) -> None:
    StockMovement.objects.filter(supply_line__supply=supply).delete()
    for line in supply.lines.select_related("ingredient"):
        if line.quantity <= 0:
            raise ValidationError(_("Supply quantity must be positive."))
        StockMovement.objects.create(
            date=supply.date,
            kind=StockMovement.KIND_SUPPLY,
            quantity=line.quantity,
            unit_cost=_quantize_cost(line.total / line.quantity),
            ingredient=line.ingredient,
            supply_line=line,
        )
    recompute_costs()


@transaction.atomic
def apply_production(production: Production) -> None:
    semi_product = production.semi_product
    if not semi_product.is_produced:
        raise ValidationError(
            _("Semi-product %(name)s is not produced in advance.") % {"name": semi_product.name}
        )
    if production.quantity <= 0:
        raise ValidationError(_("Production quantity must be positive."))
    StockMovement.objects.filter(production=production).delete()
    _create_outgoing(
        expand_semi_product(semi_product, production.quantity),
        production.date,
        StockMovement.KIND_PRODUCTION_OUT,
        {"production": production},
    )
    StockMovement.objects.create(
        date=production.date,
        kind=StockMovement.KIND_PRODUCTION_IN,
        quantity=production.quantity,
        unit_cost=_ZERO,
        semi_product=semi_product,
        production=production,
    )
    recompute_costs()


@transaction.atomic
def apply_finished_production(production: FinishedProduction) -> None:
    StockMovement.objects.filter(finished_production_line__production=production).delete()
    lines = production.lines.select_related("finished_good__tech_card").prefetch_related(
        "finished_good__modifiers__modifier"
    )
    for line in lines:
        if line.quantity < 1:
            raise ValidationError(_("Finished good quantity must be a whole number of pieces."))
        good = line.finished_good
        modifiers = [(row.modifier, row.quantity) for row in good.modifiers.all()]
        prepare_assembly(good.tech_card, good.weight_kg, modifiers)
        _create_outgoing(
            expand_order_item(good.tech_card, good.weight_kg, line.quantity, modifiers, []),
            production.date,
            StockMovement.KIND_PRODUCTION_OUT,
            {"finished_production_line": line},
        )
        StockMovement.objects.create(
            date=production.date,
            kind=StockMovement.KIND_PRODUCTION_IN,
            quantity=Decimal(line.quantity),
            unit_cost=_ZERO,
            finished_good=good,
            finished_production_line=line,
        )
    recompute_costs()
    drop_orphan_finished_goods()


@transaction.atomic
def apply_write_off(write_off: WriteOff) -> None:
    StockMovement.objects.filter(write_off_line__write_off=write_off).delete()
    for line in write_off.lines.select_related("ingredient", "semi_product", "finished_good"):
        if line.finished_good_id is not None:
            _require_whole_pieces(line.quantity, False)
            _create_finished_outgoing(
                {line.finished_good: line.quantity},
                write_off.date,
                StockMovement.KIND_WRITE_OFF,
                {"write_off_line": line},
            )
            continue
        if line.quantity <= 0:
            raise ValidationError(_("Write-off quantity must be positive."))
        _create_outgoing(
            expand_component(line.component, line.quantity),
            write_off.date,
            StockMovement.KIND_WRITE_OFF,
            {"write_off_line": line},
        )
    recompute_costs()
    drop_orphan_finished_goods()


@transaction.atomic
def close_inventory_count(count: InventoryCount) -> None:
    if count.status == InventoryCount.STATUS_CLOSED:
        raise ValidationError(_("Inventory count is already closed."))
    levels = stock_levels(count.date, count)
    for line in count.lines.select_related("ingredient", "semi_product", "finished_good"):
        component = line.component
        if isinstance(component, FinishedGood):
            _require_whole_pieces(line.actual_quantity, True)
        elif not is_stocked(component):
            raise ValidationError(
                _("Semi-product %(name)s is not produced in advance.") % {"name": component.name}
            )
        expected = stock_of(component, levels)
        line.expected_quantity = expected.quantize(Decimal("0.001"))
        line.save(update_fields=["expected_quantity"])
        difference = _quantize_quantity(line.actual_quantity - expected)
        if difference != 0:
            StockMovement.objects.create(
                date=count.date,
                kind=StockMovement.KIND_INVENTORY,
                quantity=difference,
                unit_cost=component.avg_cost,
                inventory_count_line=line,
                **_component_fields(component),
            )
    count.status = InventoryCount.STATUS_CLOSED
    count.closed_at = timezone.now()
    count.save(update_fields=["status", "closed_at"])
    recompute_costs()
    drop_orphan_finished_goods()


@transaction.atomic
def delete_document(document: Supply | Production | FinishedProduction | WriteOff | InventoryCount) -> None:
    document.delete()
    drop_orphan_finished_goods()
    recompute_costs()


def order_needs_write_off(crm_order: CrmOrder) -> bool:
    return not crm_order.deleted and crm_order.status in WRITE_OFF_STATUSES


def order_stock_needs(crm_order: CrmOrder) -> tuple[Needs, dict[FinishedGood, Decimal]]:
    needs: Needs = {}
    finished: dict[FinishedGood, Decimal] = {}
    items = crm_order.items.select_related("tech_card").prefetch_related(
        "modifiers__modifier",
        "lines__ingredient",
        "lines__semi_product",
    )
    for item in items:
        good = None
        if item.tech_card_id is not None:
            pairs = [(row.modifier_id, row.quantity) for row in item.modifiers.all()]
            weight = item.weight_kg if item.tech_card.kind == TechCard.KIND_WEIGHTED else None
            good = FinishedGood.objects.filter(
                signature=finished_signature(item.tech_card_id, weight, pairs)
            ).first()
        if good is None:
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
            continue
        finished[good] = finished.get(good, Decimal("0")) + Decimal(item.quantity)
        for line in item.lines.all():
            _merge(needs, expand_component(line.component, line.quantity))
    return needs, finished


@transaction.atomic
def sync_order_write_off(crm_order: CrmOrder) -> None:
    had_movements = StockMovement.objects.filter(crm_order=crm_order).exists()
    StockMovement.objects.filter(crm_order=crm_order).delete()
    needs: Needs = {}
    finished: dict[FinishedGood, Decimal] = {}
    if order_needs_write_off(crm_order):
        needs, finished = order_stock_needs(crm_order)
    _create_outgoing(needs, crm_order.date, StockMovement.KIND_ORDER, {"crm_order": crm_order})
    _create_finished_outgoing(finished, crm_order.date, StockMovement.KIND_ORDER, {"crm_order": crm_order})
    if had_movements or needs or finished:
        recompute_costs()
