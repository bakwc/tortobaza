import hashlib
import json
import re
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from openai import OpenAI

from crm.analytics import weight_kg
from crm.analytics_fillings import canonical_filling, canonical_names, normalize_text, stored_filling
from crm.models import AnalyticsOrderComposition, AnalyticsOrderCompositionItem, CrmOrder

_MODEL = "gpt-4.1-mini"
_WEIGHT_Q = Decimal("0.001")
_PRICE_Q = Decimal("0.01")
_WEIGHT_GROUPS = frozenset({"weight", "size", "вес", "размер"})
_FILLING_GROUPS = frozenset({"filling", "начинка", "flavor", "flovers bento"})
_FILLING_TITLES = _FILLING_GROUPS
_WEIGHT_TITLES = _WEIGHT_GROUPS
_KINDS = frozenset(choice[0] for choice in AnalyticsOrderCompositionItem.KIND_CHOICES)
_KIND_NAMES = {
    AnalyticsOrderCompositionItem.KIND_CAKE: "Торт",
    AnalyticsOrderCompositionItem.KIND_BENTO: "Бенто",
    AnalyticsOrderCompositionItem.KIND_CUPCAKE: "Капкейк",
    AnalyticsOrderCompositionItem.KIND_MACARON: "Макарон",
    AnalyticsOrderCompositionItem.KIND_ADDON: "Дополнение",
    AnalyticsOrderCompositionItem.KIND_OTHER: "Другое",
}
_GENERIC_BENTO = frozenset({"бенто", "бенто торт", "bento", "bento cake", "торт бенто"})
_PRODUCT_LINE_RE = re.compile(
    r"^(?P<name>.+?)\s×\s(?P<qty>\d+)\s[—–-]\s(?P<price>\d+(?:[.,]\d+)?)\s*$"
)
_PROP_SPLIT_RE = re.compile(r",\s+(?=[^,]+:)")
_WEIGHT_PHRASE_RE = re.compile(
    r"\d+(?:[.,]\d+)?\s*"
    r"(?:килограммов|килограмма|килограмм|кг|kgs|kg|"
    r"граммов|грамма|грамм|грам|gramm|grams|gram|гр|gr|g)"
    r"(?!\w)",
    re.IGNORECASE,
)
_TEMPLATE_RE = re.compile(
    r"с\s+ваш(?:ей|им)\s+(?:надписью|фото(?:\s+\S+)?)",
    re.IGNORECASE,
)
_EXTRA_RE = re.compile(r"капкей|макарон|бенто|банкейк|набор|ярус|×|шт", re.IGNORECASE)
_LLM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": [
                            "cake",
                            "bento",
                            "cupcake",
                            "macaron",
                            "addon",
                            "other",
                        ],
                    },
                    "name": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "weight_kg": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                    "filling": {"type": "string"},
                    "price": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                },
                "required": ["kind", "name", "quantity", "weight_kg", "filling", "price"],
            },
        }
    },
    "required": ["items"],
}


def source_hash(order: CrmOrder) -> str:
    raw = json.dumps(_source_payload(order), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def sync_analytics_composition(order: CrmOrder) -> tuple[AnalyticsOrderComposition, bool]:
    digest = source_hash(order)
    existing = AnalyticsOrderComposition.objects.filter(order_id=order.pk).first()
    if existing is not None and existing.source_hash == digest:
        return existing, False
    items, parser = parse_items(order)
    with transaction.atomic():
        composition = AnalyticsOrderComposition.objects.update_or_create(
            order=order,
            defaults={"source_hash": digest, "parser": parser},
        )[0]
        composition.items.all().delete()
        AnalyticsOrderCompositionItem.objects.bulk_create(
            [
                AnalyticsOrderCompositionItem(
                    composition=composition,
                    kind=item["kind"],
                    name=item["name"],
                    quantity=item["quantity"],
                    weight_kg=item["weight_kg"],
                    filling=item["filling"],
                    price=item["price"],
                    position=item["position"],
                )
                for item in items
            ]
        )
    return composition, True


def parse_items(order: CrmOrder) -> tuple[list[dict], str]:
    website_items = _website_items(order)
    if website_items is not None:
        return website_items, AnalyticsOrderComposition.PARSER_RULES
    line_items = _description_items(order.description)
    if line_items is not None:
        return line_items, AnalyticsOrderComposition.PARSER_RULES
    simple = _simple_item(order)
    if simple is not None:
        return [simple], AnalyticsOrderComposition.PARSER_RULES
    return _llm_items(order), AnalyticsOrderComposition.PARSER_LLM


def _source_payload(order: CrmOrder) -> dict:
    payload: dict = {
        "weight": order.weight,
        "filling": order.filling,
        "description": order.description,
    }
    website = order.website_order
    if website is None:
        return payload
    website_items = []
    for item in website.items.all():
        options = []
        for option in item.options.all():
            option_weight = None
            if option.option_id is not None and option.option.weight_kg is not None:
                option_weight = str(option.option.weight_kg)
            options.append(
                {
                    "group_name": option.group_name,
                    "option_name": option.option_name,
                    "weight_kg": option_weight,
                }
            )
        website_items.append(
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "line_total": str(item.line_total),
                "options": options,
            }
        )
    payload["website_items"] = website_items
    return payload


def _website_items(order: CrmOrder) -> list[dict] | None:
    website = order.website_order
    if website is None:
        return None
    rows = list(website.items.all())
    if not rows:
        return None
    items = []
    for position, row in enumerate(rows):
        weight = None
        fillings = []
        for option in row.options.all():
            parsed_weight = _option_weight(option)
            if weight is None and parsed_weight is not None:
                weight = parsed_weight
            parsed_filling = _option_filling(option)
            if parsed_filling is not None:
                fillings.append(parsed_filling)
        items.append(
            _position(
                row.product_name,
                row.quantity,
                weight,
                ", ".join(fillings),
                row.line_total,
                position,
            )
        )
    return items


def _option_weight(option) -> Decimal | None:
    if option.group_name.casefold() not in _WEIGHT_GROUPS:
        return None
    linked = option.option
    if linked is not None and linked.weight_kg is not None:
        return linked.weight_kg
    return weight_kg(option.option_name)


def _option_filling(option) -> str | None:
    if option.group_name.casefold() not in _FILLING_GROUPS:
        return None
    text = stored_filling(option.option_name)
    if text == "":
        return None
    return text


def _description_items(description: str) -> list[dict] | None:
    pending_name = ""
    current = None
    products: list[dict] = []
    for raw in description.splitlines():
        if raw.startswith("  ") and current is not None:
            current["props"].append(raw.strip())
            pending_name = ""
            continue
        line = raw.strip()
        if line == "":
            continue
        match = _PRODUCT_LINE_RE.match(line)
        if match:
            if current is not None:
                products.append(current)
            name = match.group("name").strip()
            if pending_name:
                name = f"{pending_name} {name}"
            pending_name = ""
            current = {
                "name": name,
                "quantity": int(match.group("qty")),
                "price": _price(match.group("price")),
                "props": [],
            }
            continue
        if current is not None:
            products.append(current)
            current = None
        if _is_meta(line):
            pending_name = ""
            continue
        pending_name = line
    if current is not None:
        products.append(current)
    if not products:
        return None
    return [_product_item(product, position) for position, product in enumerate(products)]


def _is_meta(line: str) -> bool:
    lowered = line.casefold()
    if "×" in line and lowered.startswith("открытка:"):
        return False
    return (
        lowered.startswith("flowwow #")
        or lowered.startswith("сайт заказ #")
        or lowered.startswith("email:")
        or lowered.startswith("доставка:")
        or lowered.startswith("покупатель:")
        or lowered.startswith("курьеру:")
        or lowered.startswith("промокод:")
        or lowered.startswith("открытка:")
    )


def _product_item(product: dict, position: int) -> dict:
    prop_weight, filling = _props(product["props"])
    weight = prop_weight if prop_weight is not None else weight_kg(product["name"])
    return _position(
        product["name"],
        product["quantity"],
        weight,
        filling,
        product["price"],
        position,
    )


def _props(lines: list[str]) -> tuple[Decimal | None, str]:
    weight = None
    fillings = []
    for line in lines:
        for title, value in _prop_parts(line):
            if title in _FILLING_TITLES:
                text = stored_filling(value)
                if text != "":
                    fillings.append(text)
            elif title in _WEIGHT_TITLES and weight is None:
                parsed = weight_kg(value)
                if parsed is not None:
                    weight = parsed
    return weight, ", ".join(fillings)


def _prop_parts(line: str) -> list[tuple[str, str]]:
    parts = []
    for chunk in _PROP_SPLIT_RE.split(line):
        if ":" not in chunk:
            continue
        title, value = chunk.split(":", 1)
        parts.append((title.strip().casefold(), value.strip()))
    return parts


def _simple_item(order: CrmOrder) -> dict | None:
    parsed = weight_kg(order.weight)
    if parsed is None:
        return None
    filling = canonical_filling(order.filling)
    if filling is None:
        return None
    if _EXTRA_RE.search(order.description):
        return None
    return _position("Торт", 1, parsed, filling, order.cake_price, 0)


def _position(
    name: str,
    quantity: int,
    weight: Decimal | None,
    filling: str,
    price: Decimal | None,
    position: int,
) -> dict:
    kind = _kind(name, weight, filling)
    return {
        "kind": kind,
        "name": _clean_name(name, kind),
        "quantity": quantity,
        "weight_kg": None if weight is None else weight.quantize(_WEIGHT_Q),
        "filling": filling,
        "price": None if price is None else price.quantize(_PRICE_Q),
        "position": position,
    }


def _kind(name: str, weight: Decimal | None, filling: str) -> str:
    key = normalize_text(name)
    if any(token in key for token in ("открытк", "фотопечат", "топпер", "topper", "postcard")):
        return AnalyticsOrderCompositionItem.KIND_ADDON
    if "бенто" in key or "bento" in key:
        return AnalyticsOrderCompositionItem.KIND_BENTO
    if "капкей" in key or "cupcake" in key:
        return AnalyticsOrderCompositionItem.KIND_CUPCAKE
    if "макарон" in key or "macaron" in key:
        return AnalyticsOrderCompositionItem.KIND_MACARON
    if weight is not None or filling != "":
        return AnalyticsOrderCompositionItem.KIND_CAKE
    if "торт" in key or "cake" in key:
        return AnalyticsOrderCompositionItem.KIND_CAKE
    return AnalyticsOrderCompositionItem.KIND_OTHER


def _clean_name(name: str, kind: str) -> str:
    text = _WEIGHT_PHRASE_RE.sub(" ", name)
    text = _TEMPLATE_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -—,")
    if kind == AnalyticsOrderCompositionItem.KIND_BENTO and normalize_text(text) in _GENERIC_BENTO:
        return _KIND_NAMES[kind]
    if text == "":
        return _KIND_NAMES[kind]
    return text


def _price(text: str) -> Decimal:
    return Decimal(text.replace(",", ".")).quantize(_PRICE_Q)


def _llm_items(order: CrmOrder) -> list[dict]:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.responses.create(
        model=_MODEL,
        input=_llm_input(order),
        text={
            "format": {
                "type": "json_schema",
                "name": "analytics_order_composition",
                "strict": True,
                "schema": _LLM_SCHEMA,
            }
        },
    )
    payload = json.loads(response.output_text)
    if not isinstance(payload, dict):
        raise ValueError("composition")
    return [_llm_item(raw, position) for position, raw in enumerate(_llm_raw_items(payload))]


def _llm_input(order: CrmOrder) -> str:
    names = ", ".join(canonical_names())
    return (
        "Разбери заказ кондитерской в список покупаемых позиций.\n"
        "Игнорируй дизайн, надпись на торте, доставку, контакты и текст открытки.\n"
        "Набор разбей на отдельные позиции.\n"
        "Открытка и фотопечать — addon, только если это отдельная заказанная позиция.\n"
        f"Если начинка совпадает со списком, используй имя из списка: {names}.\n"
        "kind: cake, bento, cupcake, macaron, addon, other.\n"
        "weight_kg — число в килограммах или null. price — строка с ценой позиции или null.\n"
        f"Вес: {order.weight}\n"
        f"Начинка: {order.filling}\n"
        f"Описание:\n{order.description}"
    )


def _llm_raw_items(payload: dict) -> list:
    raw_items = payload["items"]
    if not isinstance(raw_items, list):
        raise ValueError("items")
    return raw_items


def _llm_item(raw: dict, position: int) -> dict:
    kind = raw["kind"]
    if kind not in _KINDS:
        raise ValueError("kind")
    name = str(raw["name"]).strip()
    if name == "":
        raise ValueError("name")
    quantity = raw["quantity"]
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        raise ValueError("quantity")
    weight = raw["weight_kg"]
    if weight is not None:
        weight = Decimal(str(weight)).quantize(_WEIGHT_Q)
    filling = stored_filling(str(raw["filling"]))
    price = raw["price"]
    if price is not None:
        if str(price).strip() == "":
            raise ValueError("price")
        price = _price(str(price))
    return {
        "kind": kind,
        "name": name,
        "quantity": quantity,
        "weight_kg": weight,
        "filling": filling,
        "price": price,
        "position": position,
    }
