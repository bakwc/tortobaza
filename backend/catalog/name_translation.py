import json
import threading

from django.conf import settings
from django.db import models, transaction
from openai import OpenAI
from pydantic import BaseModel

NAME_LANGUAGES = ("en", "ka", "ru")
NAME_TRANSLATE_MODEL = "gpt-6.1-sol"
NAME_TRANSLATE_TIMEOUT_SECONDS = 60

NAME_TRANSLATE_PROMPT = """You translate names for the website of a cake and dessert shop in Tbilisi, Georgia. The names belong to confectionery sold on the site: cakes, bento cakes, desserts, pastries, and the categories that group them.

The user message is JSON with kind (product or category) and names: the names already filled in, keyed by language code (en English, ka Georgian, ru Russian). Return en, ka, and ru. For a language present in the input, copy its name unchanged. For every other language, write the name a customer would expect to see on a confectionery website in that language.

Use the established names of classic desserts in each language (for example Медовик, Наполеон, Тирамису) and transliterate a name that has no established translation. Keep numbers and brand names. Follow the capitalization style of the input. Return only the names, without quotes or explanations.
"""


class TranslatedName(BaseModel):
    en: str
    ka: str
    ru: str


def filled_names(instance: models.Model) -> dict[str, str]:
    names = {}
    for code in NAME_LANGUAGES:
        value = getattr(instance, f"name_{code}")
        if value and value.strip():
            names[code] = value.strip()
    return names


def schedule_name_translation(instance: models.Model) -> None:
    if not 0 < len(filled_names(instance)) < len(NAME_LANGUAGES):
        return
    model = type(instance)
    pk = instance.pk
    transaction.on_commit(
        lambda: threading.Thread(
            target=translate_names,
            args=(model, pk),
            daemon=True,
        ).start()
    )


def request_name_translation(kind: str, names: dict[str, str]) -> TranslatedName:
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=NAME_TRANSLATE_TIMEOUT_SECONDS)
    response = client.responses.parse(
        model=NAME_TRANSLATE_MODEL,
        instructions=NAME_TRANSLATE_PROMPT,
        input=json.dumps({"kind": kind, "names": names}, ensure_ascii=False),
        text_format=TranslatedName,
        store=False,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("Name translation returned no data.")
    return parsed


def translate_names(model: type[models.Model], pk: int) -> None:
    names = filled_names(model.objects.get(pk=pk))
    missing = [code for code in NAME_LANGUAGES if code not in names]
    if not names or not missing:
        return
    translated = request_name_translation(model._meta.model_name, names)
    with transaction.atomic():
        instance = model.objects.select_for_update().get(pk=pk)
        if filled_names(instance) != names:
            return
        for code in missing:
            value = getattr(translated, code).strip()
            if not value:
                raise RuntimeError(f"Name translation returned an empty {code} name.")
            setattr(instance, f"name_{code}", value)
        instance.save()
