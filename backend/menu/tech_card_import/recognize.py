import base64
import json
import logging
import time
from decimal import Decimal
from pathlib import Path
from typing import Literal

from django.conf import settings
from openai import OpenAI
from pydantic import BaseModel

from menu.models import Ingredient, SemiProduct
from menu.tech_card_import.docx_reader import docx_blocks
from menu.tech_card_import.markdown import render_markdown
from menu.tech_card_import.pages_reader import read_pages

logger = logging.getLogger(__name__)

TECH_CARD_MODEL = "gpt-6.1-sol"
TECH_CARD_TIMEOUT_SECONDS = 180
TECH_CARD_ATTEMPTS = 2

TECH_CARD_PROMPT = """You read a pastry tech card and return one structured recipe.

The user message is a JSON catalog of ingredients and semi-products already in the database. Each entry has id, name, and unit. unit is g (grams), ml (milliliters), or pcs (pieces). After the catalog comes the card: Markdown extracted from the file, a photo of the first page, or a PDF.

The cards are in Russian. Keep names and the method in Russian.

kind is weighted when the card is a mass recipe, such as a cake or a cream weighed in kilograms. kind is piece when the yield is a count of portions, such as пирожные.
basis_weight_kg is the recipe yield in kilograms for a weighted card, as a decimal string, and null for a piece card.
basis_quantity is how many pieces the recipe is written for, and null for a weighted card.
"Выход: 18 шт" is a piece card with basis_quantity 18. A title "2 шт" is a piece card with basis_quantity 2. A card written for 1 kg is weighted with basis_weight_kg "1".

sections are the named sub-recipes that have their own ingredient rows, such as коржи, крем, ганаш, начинка, or глазурь. A section's rows are its lines and its preparation text is its method.
lines are ingredient rows that belong to the card itself and not to a section.
method is the remaining text: inventory, assembly that has no ingredient table of its own, storage, and quality notes. Write it as Markdown.

A row becomes a line only when it has a measurable amount.
quantity is a decimal string with a dot. unit is g, ml, or pcs and is the unit of quantity.
"2 л" is 2000 ml. "1 кг" is 1000 g. "500 мг" is 0.5 g. "65 г" is 65 g. "≈ 73 г" is 73 g.
Eggs, yolks, and whites written as штуки stay pcs. The same items written in grams stay g.
"1 порция", "по вкусу", "по необходимости", and inventory lists are not lines. Put them in the method of the section they belong to.
loss_percent is "0" unless the card states a loss percentage. It is a decimal string.

original_text is the source row as printed. name is a short Russian name without the amount.
Set ingredient_id or semi_product_id only when the row clearly matches one catalog entry. Never invent an id. At most one of the two is set, and the other is null.
suggested_kind is semi_product when the row is a prepared component, such as бисквит, ганаш, крем, коржи, начинка, or глазурь. Otherwise suggested_kind is ingredient.
"""


class ImportedLine(BaseModel):
    original_text: str
    name: str
    quantity: str
    unit: Literal["g", "ml", "pcs"]
    loss_percent: str
    ingredient_id: int | None
    semi_product_id: int | None
    suggested_kind: Literal["ingredient", "semi_product"]


class ImportedSection(BaseModel):
    name: str
    method: str
    lines: list[ImportedLine]


class ImportedTechCard(BaseModel):
    name: str
    kind: Literal["weighted", "piece"]
    basis_weight_kg: str | None
    basis_quantity: int | None
    method: str
    lines: list[ImportedLine]
    sections: list[ImportedSection]


def decimal_text(value: str) -> str:
    return format(Decimal(value), "f")


def line_payload(line: ImportedLine, ingredients: set[int], semi_products: set[int]) -> dict:
    if line.name.strip() == "":
        raise ValueError("Imported line has no name.")
    if line.ingredient_id is not None and line.semi_product_id is not None:
        raise ValueError("Line matches both an ingredient and a semi-product.")
    if line.ingredient_id is not None and line.ingredient_id not in ingredients:
        raise ValueError(f"Unknown ingredient id {line.ingredient_id}.")
    if line.semi_product_id is not None and line.semi_product_id not in semi_products:
        raise ValueError(f"Unknown semi-product id {line.semi_product_id}.")
    return {
        "original_text": line.original_text,
        "name": line.name.strip(),
        "quantity": decimal_text(line.quantity),
        "unit": line.unit,
        "loss_percent": decimal_text(line.loss_percent),
        "ingredient_id": line.ingredient_id,
        "semi_product_id": line.semi_product_id,
        "suggested_kind": line.suggested_kind,
    }


def card_payload(parsed: ImportedTechCard, ingredients: set[int], semi_products: set[int], source_name: str) -> dict:
    if parsed.name.strip() == "":
        raise ValueError("Imported tech card has no name.")
    if parsed.kind == "weighted":
        if parsed.basis_weight_kg is None or parsed.basis_quantity is not None:
            raise ValueError("Weighted tech card needs basis_weight_kg only.")
        basis_weight_kg = decimal_text(parsed.basis_weight_kg)
        basis_quantity = None
    else:
        if parsed.basis_quantity is None or parsed.basis_weight_kg is not None:
            raise ValueError("Piece tech card needs basis_quantity only.")
        if parsed.basis_quantity < 1:
            raise ValueError("Basis quantity must be at least 1.")
        basis_weight_kg = None
        basis_quantity = parsed.basis_quantity
    return {
        "name": parsed.name.strip(),
        "kind": parsed.kind,
        "basis_weight_kg": basis_weight_kg,
        "basis_quantity": basis_quantity,
        "method": parsed.method,
        "lines": [line_payload(line, ingredients, semi_products) for line in parsed.lines],
        "sections": [
            {
                "name": section.name.strip(),
                "method": section.method,
                "lines": [line_payload(line, ingredients, semi_products) for line in section.lines],
            }
            for section in parsed.sections
        ],
        "source_name": source_name,
    }


def document_input(filename: str, data: bytes) -> list[dict]:
    extension = Path(filename).suffix.lower()
    if extension == ".docx":
        return [{"type": "input_text", "text": render_markdown(docx_blocks(data))}]
    if extension == ".pages":
        document = read_pages(data)
        encoded = base64.b64encode(document.preview).decode("ascii")
        return [
            {"type": "input_text", "text": render_markdown(document.blocks)},
            {
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{encoded}",
                "detail": "high",
            },
        ]
    if extension == ".pdf":
        encoded = base64.b64encode(data).decode("ascii")
        return [
            {
                "type": "input_file",
                "filename": Path(filename).name,
                "file_data": f"data:application/pdf;base64,{encoded}",
                "detail": "high",
            }
        ]
    raise ValueError(f"Unsupported file {extension}.")


def recognize_tech_card(filename: str, data: bytes) -> dict:
    ingredients = list(Ingredient.objects.filter(is_active=True).order_by("name"))
    semi_products = list(SemiProduct.objects.filter(is_active=True).order_by("name"))
    catalog = json.dumps(
        {
            "ingredients": [{"id": row.pk, "name": row.name, "unit": row.unit} for row in ingredients],
            "semi_products": [{"id": row.pk, "name": row.name, "unit": row.unit} for row in semi_products],
        },
        ensure_ascii=False,
    )
    content = [{"type": "input_text", "text": catalog}, *document_input(filename, data)]
    ingredient_ids = {row.pk for row in ingredients}
    semi_product_ids = {row.pk for row in semi_products}
    source_name = Path(filename).name
    conversation: list[dict] = [{"role": "user", "content": content}]
    logger.info(
        "tech card openai request model=%s file=%s bytes=%s ingredients=%s semi_products=%s key_set=%s",
        TECH_CARD_MODEL,
        filename,
        len(data),
        len(ingredients),
        len(semi_products),
        bool(settings.OPENAI_API_KEY),
    )
    started = time.monotonic()
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=TECH_CARD_TIMEOUT_SECONDS)
    for attempt in range(TECH_CARD_ATTEMPTS):
        response = client.responses.parse(
            model=TECH_CARD_MODEL,
            instructions=TECH_CARD_PROMPT,
            input=conversation,
            text_format=ImportedTechCard,
            store=False,
        )
        logger.info(
            "tech card openai response attempt=%s elapsed=%.1fs",
            attempt + 1,
            time.monotonic() - started,
        )
        parsed = response.output_parsed
        if parsed is None:
            error = ValueError("Tech card recognition returned no data.")
        else:
            try:
                return card_payload(parsed, ingredient_ids, semi_product_ids, source_name)
            except ValueError as caught:
                error = caught
        if attempt + 1 == TECH_CARD_ATTEMPTS:
            break
        logger.info("tech card openai correction error=%s", error)
        conversation.append({"role": "assistant", "content": response.output_text})
        conversation.append({"role": "user", "content": str(error)})
    raise error
