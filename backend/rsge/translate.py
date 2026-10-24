import json

from django.conf import settings
from django.db.models import Model, Q
from openai import OpenAI
from pydantic import BaseModel

from rsge.models import Invoice, Waybill

TRANSLATE_MODEL = "gpt-5.5"
TRANSLATE_TIMEOUT_SECONDS = 90

TRANSLATE_PROMPT = """You translate strings from Georgian tax waybills and invoices into Russian.

These documents record deliveries of products to a confectionery workshop: ingredients, packaging, and related goods and services.

The user message is a JSON array of Georgian strings, in order. Return ru as an array of Russian translations of the same length and in the same order.

Use the Russian names usual for confectionery production. Transliterate company and person names. Render the Georgian legal form შპს as ООО. Keep numbers, percentages, trademarks, and Latin brands. Translate units of measure (კგ, ცალი, მომსახურება, and similar). Do not add explanations. If a string is already Russian or has no Georgian to translate, copy it unchanged.
"""

WAYBILL_FIELDS = (
    "buyer_name",
    "seller_name",
    "start_address",
    "end_address",
    "driver_name",
    "reception_info",
    "waybill_comment",
)

GOOD_FIELDS = ("name", "unit_txt")

INVOICE_FIELDS = ("org_name", "notes", "note")

LINE_FIELDS = ("goods", "unit")


class TranslationBatch(BaseModel):
    ru: list[str]


def missing_q(prefix: str, fields: tuple[str, ...]) -> Q:
    query = Q()
    for field in fields:
        source = f"{prefix}{field}"
        query |= Q(**{f"{source}__gt": "", f"{source}_ru": ""})
    return query


def pending_fields(instance: Model, fields: tuple[str, ...]) -> list[tuple[str, str]]:
    pending = []
    for field in fields:
        source = getattr(instance, field)
        if source and getattr(instance, f"{field}_ru") == "":
            pending.append((field, source))
    return pending


def translate_strings(strings: list[str]) -> list[str]:
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=TRANSLATE_TIMEOUT_SECONDS)
    response = client.responses.parse(
        model=TRANSLATE_MODEL,
        instructions=TRANSLATE_PROMPT,
        input=json.dumps(strings, ensure_ascii=False),
        text_format=TranslationBatch,
        store=False,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("Translation returned no data.")
    if len(parsed.ru) != len(strings):
        raise RuntimeError(f"Translation length {len(parsed.ru)} does not match {len(strings)}.")
    return parsed.ru


def translate_document(rows: list[tuple[Model, tuple[str, ...]]]) -> None:
    targets: list[tuple[Model, str, str]] = []
    for instance, fields in rows:
        for field, source in pending_fields(instance, fields):
            targets.append((instance, field, source))
    if not targets:
        return
    unique: list[str] = []
    index: dict[str, int] = {}
    for _instance, _field, source in targets:
        if source not in index:
            index[source] = len(unique)
            unique.append(source)
    translated = translate_strings(unique)
    updates: dict[int, tuple[Model, list[str]]] = {}
    for instance, field, source in targets:
        ru_field = f"{field}_ru"
        setattr(instance, ru_field, translated[index[source]])
        key = id(instance)
        if key not in updates:
            updates[key] = (instance, [])
        updates[key][1].append(ru_field)
    for instance, fields in updates.values():
        instance.save(update_fields=fields)


def translate_waybills() -> None:
    query = missing_q("", WAYBILL_FIELDS) | missing_q("goods__", GOOD_FIELDS)
    waybills = Waybill.objects.filter(query).distinct().prefetch_related("goods").order_by("pk")
    for waybill in waybills:
        rows: list[tuple[Model, tuple[str, ...]]] = [(waybill, WAYBILL_FIELDS)]
        for good in waybill.goods.all():
            rows.append((good, GOOD_FIELDS))
        translate_document(rows)


def translate_invoices() -> None:
    query = missing_q("", INVOICE_FIELDS) | missing_q("lines__", LINE_FIELDS)
    invoices = Invoice.objects.filter(query).distinct().prefetch_related("lines").order_by("pk")
    for invoice in invoices:
        rows: list[tuple[Model, tuple[str, ...]]] = [(invoice, INVOICE_FIELDS)]
        for line in invoice.lines.all():
            rows.append((line, LINE_FIELDS))
        translate_document(rows)
