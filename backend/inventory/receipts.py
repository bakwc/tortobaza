import base64
import json
from decimal import Decimal
from io import BytesIO
from typing import Literal

import pillow_heif
from django.conf import settings
from django.core.files.base import ContentFile
from openai import OpenAI
from PIL import Image, ImageOps
from pydantic import BaseModel

from menu.models import Ingredient

pillow_heif.register_heif_opener()

RECEIPT_MODEL = "gpt-5.5"
MAX_EDGE = 2000

RECEIPT_PROMPT = """You read a photo of a shop receipt and return structured data.

The receipt is usually in Georgian. Translate each item name into Russian (name_ru) and keep the printed text (original_name).

The user message is a JSON list of ingredients: {id, name, unit}. unit is g (grams), ml (milliliters), or pcs (pieces).
Set ingredient_id only when an item clearly matches one entry in that list. Otherwise ingredient_id is null. Never invent an id.

quantity is the amount in the matched ingredient's unit, or in g, ml, or pcs when nothing matches:
- A line sold in pieces whose name contains a package weight or volume is converted. "200გრ" and quantity 1 is 200 g. "200მლ" is 200 ml. "0.5ლ" is 500 ml.
- A leading zero before grams or milliliters is kilograms or liters written with the smaller unit. "0.800გრ" is 800 g. "0.800მლ" is 800 ml.
- Countable goods such as eggs stay in pcs.
total is the line amount, not the unit price.
date is the receipt date as YYYY-MM-DD, or an empty string when there is no date.
merchant_name is the store or company name as printed.
total is the receipt grand total. Use 0 when it is missing.
A card terminal slip or any photo without item lines has is_itemized false and lines [].
A photo that lists items has is_itemized true and one line per item.
"""


class RecognizedLine(BaseModel):
    original_name: str
    name_ru: str
    ingredient_id: int | None
    quantity: Decimal
    unit: Literal["g", "ml", "pcs"]
    total: Decimal


class RecognizedReceipt(BaseModel):
    is_itemized: bool
    merchant_name: str
    date: str
    total: Decimal
    lines: list[RecognizedLine]


def to_jpeg(upload) -> ContentFile:
    image = ImageOps.exif_transpose(Image.open(upload)).convert("RGB")
    image.thumbnail((MAX_EDGE, MAX_EDGE))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return ContentFile(buffer.getvalue(), name="receipt.jpg")


def recognized_payload(parsed: RecognizedReceipt) -> dict:
    return {
        "is_itemized": parsed.is_itemized,
        "merchant_name": parsed.merchant_name,
        "date": parsed.date,
        "total": format(parsed.total, "f"),
        "lines": [
            {
                "original_name": line.original_name,
                "name_ru": line.name_ru,
                "ingredient_id": line.ingredient_id,
                "quantity": format(line.quantity, "f"),
                "unit": line.unit,
                "total": format(line.total, "f"),
            }
            for line in parsed.lines
        ],
    }


def recognize_receipt(jpeg_bytes: bytes) -> dict:
    ingredients = list(Ingredient.objects.filter(is_active=True).order_by("name"))
    known = {row.pk for row in ingredients}
    catalog = json.dumps(
        [{"id": row.pk, "name": row.name, "unit": row.unit} for row in ingredients],
        ensure_ascii=False,
    )
    encoded = base64.b64encode(jpeg_bytes).decode("ascii")
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.responses.parse(
        model=RECEIPT_MODEL,
        instructions=RECEIPT_PROMPT,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": catalog},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{encoded}",
                        "detail": "high",
                    },
                ],
            }
        ],
        text_format=RecognizedReceipt,
        store=False,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise ValueError("Receipt recognition returned no data.")
    for line in parsed.lines:
        if line.ingredient_id is not None and line.ingredient_id not in known:
            raise ValueError(f"Unknown ingredient id {line.ingredient_id}.")
    return recognized_payload(parsed)
