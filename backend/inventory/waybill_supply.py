import json
from datetime import date
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from django.conf import settings
from openai import OpenAI
from pydantic import BaseModel
from rest_framework.exceptions import ValidationError

from inventory.models import Supplier, Supply, SupplyLine, WaybillIngredientAlias
from inventory.services import apply_supply
from menu.models import Ingredient
from rsge.models import Waybill, WaybillGood

_TB = ZoneInfo("Asia/Tbilisi")
WAYBILL_MATCH_MODEL = "gpt-4.1-mini"
WAYBILL_MATCH_TIMEOUT_SECONDS = 90
FACTOR_PLACES = Decimal("0.000001")
MONEY_PLACES = Decimal("0.01")
SUPPLIER_NAME_LIMIT = 200

WAYBILL_MATCH_PROMPT = """You match lines from a Georgian tax waybill to a bakery ingredient catalog.

The user message is JSON: {"ingredients": [{id, name, unit}], "lines": [{good_id, name, name_ru, unit_txt, quantity, bar_code}]}.
unit is g (grams), ml (milliliters), or pcs (pieces).

For each line return up to 3 suggestions, best first.
ingredient_id is an id from ingredients, or null when nothing in the catalog fits.
Never invent an id.
factor is the multiplier from the waybill quantity to the ingredient quantity, as a decimal string.
Waybill quantity times factor equals the quantity in the ingredient unit.
Read the package size from the name. "1ლ" with quantity 10 and ingredient unit ml is factor "1000". "200გრ" with quantity 1 and ingredient unit g is factor "200". "კგ" or "кг" into grams is factor "1000". "ლ" or "л" into milliliters is factor "1000". A piece that is already the ingredient unit is factor "1".
When ingredient_id is set, unit is that ingredient's unit.
When ingredient_id is null, unit is g, ml, or pcs for a new ingredient, and factor converts the waybill quantity into that unit.
Return every good_id from lines exactly once.
"""


class WaybillSuggestionModel(BaseModel):
    ingredient_id: int | None
    factor: str
    unit: Literal["g", "ml", "pcs"]


class WaybillGoodMatchModel(BaseModel):
    good_id: int
    suggestions: list[WaybillSuggestionModel]


class WaybillMatchModel(BaseModel):
    lines: list[WaybillGoodMatchModel]


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def seller_display_name(waybill: Waybill) -> str:
    if waybill.seller_name_ru != "":
        return waybill.seller_name_ru
    return waybill.seller_name


def waybill_supply_date(waybill: Waybill) -> date:
    moment = waybill.create_date if waybill.delivery_date is None else waybill.delivery_date
    return moment.astimezone(_TB).date()


def alias_for(aliases: list[WaybillIngredientAlias], good: WaybillGood) -> WaybillIngredientAlias | None:
    if good.bar_code != "":
        for alias in aliases:
            if alias.bar_code == good.bar_code:
                return alias
        return None
    for alias in aliases:
        if alias.bar_code == "" and alias.name == good.name and alias.unit_txt == good.unit_txt:
            return alias
    return None


def alias_payload(alias: WaybillIngredientAlias | None) -> dict | None:
    if alias is None:
        return None
    return {
        "ingredient_id": alias.ingredient_id,
        "factor": None if alias.factor is None else decimal_text(alias.factor),
        "ignored": alias.ignored,
    }


def supplier_preview(waybill: Waybill) -> dict | None:
    row = Supplier.objects.filter(tin=waybill.seller_tin).first()
    if row is None:
        row = Supplier.objects.filter(name=seller_display_name(waybill)).first()
    if row is None or (row.tin is not None and row.tin != waybill.seller_tin):
        return None
    return {"id": row.pk, "name": row.name}


def suggestion_payload(suggestion: WaybillSuggestionModel, known: dict[int, Ingredient]) -> dict:
    if suggestion.ingredient_id is not None and suggestion.ingredient_id not in known:
        raise ValidationError(f"Unknown ingredient id {suggestion.ingredient_id}.")
    factor = Decimal(suggestion.factor)
    if factor <= 0:
        raise ValidationError("Factor must be positive.")
    unit = suggestion.unit
    if suggestion.ingredient_id is not None:
        unit = known[suggestion.ingredient_id].unit
    return {
        "ingredient_id": suggestion.ingredient_id,
        "factor": decimal_text(factor),
        "unit": unit,
    }


def match_waybill_goods(goods: list[WaybillGood]) -> dict[int, list[dict]]:
    ingredients = list(Ingredient.objects.filter(is_active=True).order_by("name"))
    known = {row.pk: row for row in ingredients}
    payload = json.dumps(
        {
            "ingredients": [{"id": row.pk, "name": row.name, "unit": row.unit} for row in ingredients],
            "lines": [
                {
                    "good_id": good.pk,
                    "name": good.name,
                    "name_ru": good.name_ru,
                    "unit_txt": good.unit_txt,
                    "quantity": decimal_text(good.quantity),
                    "bar_code": good.bar_code,
                }
                for good in goods
            ],
        },
        ensure_ascii=False,
    )
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=WAYBILL_MATCH_TIMEOUT_SECONDS)
    response = client.responses.parse(
        model=WAYBILL_MATCH_MODEL,
        instructions=WAYBILL_MATCH_PROMPT,
        input=[
            {
                "role": "user",
                "content": [{"type": "input_text", "text": payload}],
            }
        ],
        text_format=WaybillMatchModel,
        store=False,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise ValidationError("Waybill match returned no data.")
    expected = {good.pk for good in goods}
    returned = [row.good_id for row in parsed.lines]
    if len(returned) != len(set(returned)) or set(returned) != expected:
        raise ValidationError("Waybill match did not return every line.")
    matches: dict[int, list[dict]] = {}
    for row in parsed.lines:
        if len(row.suggestions) > 3:
            raise ValidationError("At most 3 suggestions per line.")
        matches[row.good_id] = [suggestion_payload(suggestion, known) for suggestion in row.suggestions]
    return matches


def supply_draft(waybill: Waybill) -> dict:
    goods = list(waybill.goods.all())
    aliases = list(WaybillIngredientAlias.objects.filter(seller_tin=waybill.seller_tin))
    unmatched: list[WaybillGood] = []
    chosen: list[WaybillIngredientAlias | None] = []
    for good in goods:
        alias = alias_for(aliases, good)
        chosen.append(alias)
        if alias is None:
            unmatched.append(good)
    suggestions = match_waybill_goods(unmatched) if unmatched else {}
    return {
        "date": waybill_supply_date(waybill).isoformat(),
        "supplier": supplier_preview(waybill),
        "supplier_name": seller_display_name(waybill),
        "lines": [
            {
                "good_id": good.pk,
                "name": good.name,
                "name_ru": good.name_ru,
                "unit_txt": good.unit_txt,
                "unit_txt_ru": good.unit_txt_ru,
                "quantity": decimal_text(good.quantity),
                "amount": decimal_text(good.amount),
                "bar_code": good.bar_code,
                "alias": alias_payload(alias),
                "suggestions": [] if alias is not None else suggestions[good.pk],
            }
            for good, alias in zip(goods, chosen, strict=True)
        ],
    }


def resolve_supplier(waybill: Waybill) -> Supplier:
    by_tin = Supplier.objects.filter(tin=waybill.seller_tin).first()
    if by_tin is not None:
        return by_tin
    name = seller_display_name(waybill)
    if len(name) > SUPPLIER_NAME_LIMIT:
        raise ValidationError("Supplier name is too long.")
    by_name = Supplier.objects.filter(name=name).first()
    if by_name is not None:
        if by_name.tin is not None:
            raise ValidationError("Supplier name is already used by another TIN.")
        by_name.tin = waybill.seller_tin
        by_name.save(update_fields=["tin"])
        return by_name
    return Supplier.objects.create(name=name, tin=waybill.seller_tin)


def upsert_alias(
    waybill: Waybill,
    good: WaybillGood,
    ingredient: Ingredient | None,
    factor: Decimal | None,
    ignored: bool,
) -> None:
    fields = {
        "name": good.name,
        "unit_txt": good.unit_txt,
        "bar_code": good.bar_code,
        "ingredient": ingredient,
        "factor": factor,
        "ignored": ignored,
    }
    if good.bar_code != "":
        alias = WaybillIngredientAlias.objects.filter(seller_tin=waybill.seller_tin, bar_code=good.bar_code).first()
    else:
        alias = WaybillIngredientAlias.objects.filter(
            seller_tin=waybill.seller_tin,
            bar_code="",
            name=good.name,
            unit_txt=good.unit_txt,
        ).first()
    if alias is None:
        WaybillIngredientAlias.objects.create(seller_tin=waybill.seller_tin, **fields)
        return
    for key, value in fields.items():
        setattr(alias, key, value)
    alias.save()


def create_waybill_supply(waybill: Waybill, lines: list[dict], user) -> Supply:
    if Supply.objects.filter(waybill=waybill).exists():
        raise ValidationError("This waybill already has a supply.")
    goods = list(waybill.goods.all())
    goods_by_id = {good.pk: good for good in goods}
    if sorted(line["good_id"] for line in lines) != sorted(goods_by_id):
        raise ValidationError("Send every waybill line once.")
    accepted = [line for line in lines if not line["skipped"]]
    if not accepted:
        raise ValidationError("Add at least one line.")
    prepared: list[tuple[WaybillGood, dict, Decimal | None]] = []
    for line in lines:
        good = goods_by_id[line["good_id"]]
        factor = None
        if not line["skipped"]:
            if good.quantity <= 0:
                raise ValidationError("Waybill quantity must be positive.")
            if good.amount < 0:
                raise ValidationError("Waybill amount must be zero or positive.")
            factor = (line["quantity"] / good.quantity).quantize(FACTOR_PLACES)
        prepared.append((good, line, factor))
    supplier = resolve_supplier(waybill)
    supply = Supply.objects.create(
        date=waybill_supply_date(waybill),
        supplier=supplier,
        comment=waybill.waybill_number,
        waybill=waybill,
        created_by=user,
    )
    for good, line, factor in prepared:
        if line["skipped"]:
            upsert_alias(waybill, good, None, None, True)
            continue
        SupplyLine.objects.create(
            supply=supply,
            ingredient=line["ingredient"],
            quantity=line["quantity"],
            total=good.amount.quantize(MONEY_PLACES),
        )
        upsert_alias(waybill, good, line["ingredient"], factor, False)
    apply_supply(supply)
    return supply
