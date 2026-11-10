import json
import threading

from django.conf import settings
from django.db import models, transaction
from django.db.models import Q
from django.utils.text import slugify
from openai import OpenAI
from pydantic import BaseModel

from catalog.models import Category, CategoryLanding, Option, OptionGroup, Product, ProductImage

LANGUAGES = ("en", "ka", "ru")
TRANSLATE_MODEL = "gpt-6.1-sol"
TRANSLATE_TIMEOUT_SECONDS = 90
PAGE_SLUG_LENGTH = 140

TRANSLATED_FIELDS = {
    Category: ("name", "page_heading", "page_description", "seo_title", "seo_description", "page_slug"),
    CategoryLanding: ("page_heading", "page_description", "seo_title", "seo_description", "page_slug"),
    Product: ("name", "description"),
    OptionGroup: ("name",),
    Option: ("name",),
    ProductImage: ("alt",),
}

KIND_FIELDS = {model._meta.model_name: fields for model, fields in TRANSLATED_FIELDS.items()}

TRANSLATE_PROMPT = """You translate text for the website of a cake and dessert shop in Tbilisi, Georgia. The site sells cakes, bento cakes, desserts and pastries.

The user message is JSON with items. Each item has key, kind, and fields. kind is one of: category, categorylanding (a category landing page), product, optiongroup (a group of product options such as size or filling), option (one choice in such a group), productimage (the alternative text of a product photo). fields maps a field name to the texts already written, keyed by language code: en English, ka Georgian, ru Russian.

Return one item for every input item, with the same key. For every input field return field, en, ka, and ru. Copy a language that is present in the input unchanged, including its capitalization. Write every missing language the way a customer of that language would read it on the shop website.

name is the product, category, or option name. description and page_description are selling descriptions. page_heading is the page title shown to customers. seo_title and seo_description are the search-engine title and description. alt describes the photo. page_slug is the page address: translate the meaning into the target language, then write only a lowercase Latin transliteration with hyphens between words, such as medovik or bento-tortebi.

Use the established names of classic desserts in each language, such as Медовик, Наполеон, and Тирамису. Transliterate a name that has no established translation. Keep numbers, brand names, and line breaks. Match the length and tone of the input. Do not add explanations, quotes, or fields that were not requested.
"""


class FieldTranslation(BaseModel):
    field: str
    en: str
    ka: str
    ru: str


class ItemTranslation(BaseModel):
    key: str
    fields: list[FieldTranslation]


class TranslationBatch(BaseModel):
    items: list[ItemTranslation]


def pending_fields(instance: models.Model) -> dict[str, dict[str, str]]:
    pending = {}
    for field in TRANSLATED_FIELDS[type(instance)]:
        filled = {}
        for code in LANGUAGES:
            value = getattr(instance, f"{field}_{code}")
            if value and value.strip():
                filled[code] = value.strip()
        if filled and len(filled) < len(LANGUAGES):
            pending[field] = filled
    return pending


def schedule_translation(instances: list[models.Model]) -> None:
    targets = []
    for instance in instances:
        if pending_fields(instance):
            targets.append((type(instance), instance.pk))
    if not targets:
        return
    transaction.on_commit(
        lambda: threading.Thread(
            target=translate_saved,
            args=(targets,),
            daemon=True,
        ).start()
    )


def request_translations(items: list[dict]) -> dict[str, dict[str, dict[str, str]]]:
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=TRANSLATE_TIMEOUT_SECONDS)
    response = client.responses.parse(
        model=TRANSLATE_MODEL,
        instructions=TRANSLATE_PROMPT,
        input=json.dumps({"items": items}, ensure_ascii=False),
        text_format=TranslationBatch,
        store=False,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("Translation returned no data.")
    expected = {item["key"]: set(item["fields"]) for item in items}
    return indexed_translations(parsed, expected)


def indexed_translations(
    parsed: TranslationBatch,
    expected: dict[str, set[str]],
) -> dict[str, dict[str, dict[str, str]]]:
    found: dict[str, dict[str, dict[str, str]]] = {}
    for item in parsed.items:
        if item.key not in expected or item.key in found:
            raise RuntimeError(f"Translation returned an unexpected item {item.key}.")
        fields: dict[str, dict[str, str]] = {}
        for row in item.fields:
            if row.field not in expected[item.key] or row.field in fields:
                raise RuntimeError(f"Translation returned an unexpected field {row.field}.")
            fields[row.field] = {"en": row.en, "ka": row.ka, "ru": row.ru}
        if set(fields) != expected[item.key]:
            raise RuntimeError(f"Translation fields for {item.key} do not match.")
        found[item.key] = fields
    if set(found) != set(expected):
        raise RuntimeError("Translation items do not match.")
    return found


def translate_saved(targets: list[tuple[type[models.Model], int]]) -> None:
    payload = []
    snapshots = []
    for model, pk in targets:
        instance = model.objects.get(pk=pk)
        pending = pending_fields(instance)
        if not pending:
            continue
        key = f"{model._meta.model_name}:{pk}"
        snapshots.append((model, pk, key, pending))
        payload.append({"key": key, "kind": model._meta.model_name, "fields": pending})
    if not payload:
        return
    translated = request_translations(payload)
    assigned: dict[tuple[str, int | None], set[str]] = {}
    for model, pk, key, pending in snapshots:
        apply_saved(model, pk, pending, translated[key], assigned)


def apply_saved(
    model: type[models.Model],
    pk: int,
    pending: dict[str, dict[str, str]],
    fields: dict[str, dict[str, str]],
    assigned: dict[tuple[str, int | None], set[str]],
) -> None:
    with transaction.atomic():
        instance = model.objects.select_for_update().get(pk=pk)
        if pending_fields(instance) != pending:
            return
        holder = (model._meta.model_name, pk)
        updates = translated_updates(holder, pending, fields, assigned)
        for field, code, value in updates:
            setattr(instance, f"{field}_{code}", value)
        instance.save(update_fields=[f"{field}_{code}" for field, code, _value in updates])


def translate_now(language: str, items: list[dict]) -> list[dict]:
    payload = []
    originals: dict[str, dict[str, str]] = {}
    for item in items:
        fields = {}
        originals[item["key"]] = {}
        for field, text in item["fields"].items():
            stripped = text.strip()
            if not stripped:
                continue
            fields[field] = {language: stripped}
            originals[item["key"]][field] = text
        payload.append({"key": item["key"], "kind": item["kind"], "fields": fields})
    translated = request_translations(payload)
    assigned: dict[tuple[str, int | None], set[str]] = {}
    result = []
    for item in items:
        holder = (item["kind"], item["id"])
        out = {}
        for field, original in originals[item["key"]].items():
            values = {code: translated[item["key"]][field][code] for code in LANGUAGES}
            for code in LANGUAGES:
                if code == language:
                    continue
                value = values[code].strip()
                if not value:
                    raise RuntimeError(f"Translation returned an empty {field} {code}.")
                if field == "page_slug":
                    value = unique_page_slug(value, holder, assigned)
                    assigned.setdefault(holder, set()).add(value)
                values[code] = value
            values[language] = original
            out[field] = values
        result.append({"key": item["key"], "fields": out})
    return result


def translated_updates(
    holder: tuple[str, int | None],
    pending: dict[str, dict[str, str]],
    fields: dict[str, dict[str, str]],
    assigned: dict[tuple[str, int | None], set[str]],
) -> list[tuple[str, str, str]]:
    updates = []
    for field, sources in pending.items():
        for code in LANGUAGES:
            if code in sources:
                continue
            value = fields[field][code].strip()
            if not value:
                raise RuntimeError(f"Translation returned an empty {field} {code}.")
            if field == "page_slug":
                value = unique_page_slug(value, holder, assigned)
                assigned.setdefault(holder, set()).add(value)
            updates.append((field, code, value))
    return updates


def unique_page_slug(
    value: str,
    holder: tuple[str, int | None],
    assigned: dict[tuple[str, int | None], set[str]],
) -> str:
    base = slugify(value).strip("-")
    if not base:
        raise RuntimeError("Page slug translation is empty.")
    number = 1
    while number <= 100:
        suffix = "" if number == 1 else f"-{number}"
        trimmed = base[: PAGE_SLUG_LENGTH - len(suffix)].strip("-")
        candidate = f"{trimmed}{suffix}"
        if candidate and not page_slug_taken(candidate, holder) and not slug_claimed(candidate, holder, assigned):
            return candidate
        number += 1
    raise RuntimeError("Page slug translation is not unique.")


def page_slug_taken(slug: str, holder: tuple[str, int | None]) -> bool:
    kind, record_id = holder
    query = Q(page_slug_en=slug) | Q(page_slug_ka=slug) | Q(page_slug_ru=slug)
    categories = Category.objects.filter(query)
    landings = CategoryLanding.objects.filter(query)
    if record_id is not None and kind == "category":
        categories = categories.exclude(pk=record_id)
    if record_id is not None and kind == "categorylanding":
        landings = landings.exclude(pk=record_id)
    return categories.exists() or landings.exists()


def slug_claimed(
    slug: str,
    holder: tuple[str, int | None],
    assigned: dict[tuple[str, int | None], set[str]],
) -> bool:
    for other, slugs in assigned.items():
        if other != holder and slug in slugs:
            return True
    return False
