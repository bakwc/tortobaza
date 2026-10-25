from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext as _

from crm.models import CrmOrder
from inventory.models import (
    InventoryCount,
    Production,
    StockMovement,
    Supply,
    WriteOff,
)
from menu.models import Ingredient, SemiProduct
from menu.recipes import Component, Needs, expand_component, expand_order, expand_semi_product

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


def _key(ingredient_id: int | None, semi_product_id: int | None) -> tuple[str, int]:
    if ingredient_id is not None:
        return ("ingredient", ingredient_id)
    return ("semi_product", semi_product_id)


def _component_key(component: Component) -> tuple[str, int]:
    if isinstance(component, Ingredient):
        return ("ingredient", component.pk)
    return ("semi_product", component.pk)


def _component_fields(component: Component) -> dict:
    if isinstance(component, Ingredient):
        return {"ingredient": component, "semi_product": None}
    return {"ingredient": None, "semi_product": component}


def _quantize_quantity(value: Decimal) -> Decimal:
    return value.quantize(_QUANTITY_PLACES)


def _quantize_cost(value: Decimal) -> Decimal:
    return value.quantize(_COST_PLACES)


def is_stocked(component: Component) -> bool:
    return isinstance(component, Ingredient) or component.is_produced


def _stored_costs() -> dict[tuple[str, int], Decimal]:
    costs = {("ingredient", pk): cost for pk, cost in Ingredient.objects.values_list("pk", "avg_cost")}
    costs.update({("semi_product", pk): cost for pk, cost in SemiProduct.objects.values_list("pk", "avg_cost")})
    return costs


def recompute_costs() -> None:
    stored_costs = _stored_costs()
    quantities: dict[tuple[str, int], Decimal] = {}
    averages: dict[tuple[str, int], Decimal] = {}
    production_costs: dict[int, Decimal] = {}
    changed: list[StockMovement] = []
    for movement in StockMovement.objects.select_related("inventory_count_line").order_by("date", "id"):
        key = _key(movement.ingredient_id, movement.semi_product_id)
        quantity = quantities.get(key, _ZERO)
        average = averages[key] if key in averages else stored_costs[key]
        if movement.kind == StockMovement.KIND_SUPPLY:
            incoming_cost = movement.unit_cost
        elif movement.kind == StockMovement.KIND_PRODUCTION_IN:
            incoming_cost = _quantize_cost(production_costs.get(movement.production_id, _ZERO) / movement.quantity)
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
                production_costs[movement.production_id] = (
                    production_costs.get(movement.production_id, _ZERO) - movement.quantity * unit_cost
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


def stock_levels(on_date: date | None, exclude_count: InventoryCount | None) -> dict[tuple[str, int], Decimal]:
    movements = StockMovement.objects.all()
    if on_date is not None:
        movements = movements.filter(date__lte=on_date)
    if exclude_count is not None:
        movements = movements.exclude(inventory_count_line__count=exclude_count)
    rows = movements.values("ingredient_id", "semi_product_id").annotate(total=Sum("quantity"))
    return {_key(row["ingredient_id"], row["semi_product_id"]): row["total"] for row in rows}


def stock_of(component: Component, levels: dict[tuple[str, int], Decimal]) -> Decimal:
    return levels.get(_component_key(component), _ZERO)


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
def apply_write_off(write_off: WriteOff) -> None:
    StockMovement.objects.filter(write_off_line__write_off=write_off).delete()
    for line in write_off.lines.select_related("ingredient", "semi_product"):
        if line.quantity <= 0:
            raise ValidationError(_("Write-off quantity must be positive."))
        _create_outgoing(
            expand_component(line.component, line.quantity),
            write_off.date,
            StockMovement.KIND_WRITE_OFF,
            {"write_off_line": line},
        )
    recompute_costs()


@transaction.atomic
def close_inventory_count(count: InventoryCount) -> None:
    if count.status == InventoryCount.STATUS_CLOSED:
        raise ValidationError(_("Inventory count is already closed."))
    levels = stock_levels(count.date, count)
    for line in count.lines.select_related("ingredient", "semi_product"):
        component = line.component
        if not is_stocked(component):
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


@transaction.atomic
def delete_document(document: Supply | Production | WriteOff | InventoryCount) -> None:
    document.delete()
    recompute_costs()


def order_needs_write_off(crm_order: CrmOrder) -> bool:
    return not crm_order.deleted and crm_order.status in WRITE_OFF_STATUSES


@transaction.atomic
def sync_order_write_off(crm_order: CrmOrder) -> None:
    had_movements = StockMovement.objects.filter(crm_order=crm_order).exists()
    StockMovement.objects.filter(crm_order=crm_order).delete()
    needs = expand_order(crm_order) if order_needs_write_off(crm_order) else {}
    _create_outgoing(needs, crm_order.date, StockMovement.KIND_ORDER, {"crm_order": crm_order})
    if had_movements or needs:
        recompute_costs()
