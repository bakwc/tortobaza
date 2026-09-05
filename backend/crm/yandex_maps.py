import logging

from django.conf import settings
from openai import OpenAI

from crm.google_maps import unwrap_maps_url
from crm.models import ResolvedYandexAddress

logger = logging.getLogger(__name__)

YANDEX_MAPS_PROMPT_ID = "pmpt_6a8fc1da64a8819492de6245ec4b8d5a008cb33b36bf3697"
YANDEX_MAPS_PROMPT_VERSION = "1"


def cached_yandex_maps_url(address: str) -> str | None:
    cached = ResolvedYandexAddress.objects.filter(address=address).first()
    if cached:
        return cached.yandex_url
    return None


def resolve_yandex_maps_url(address: str) -> str:
    cached = cached_yandex_maps_url(address)
    if cached:
        return cached
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    openai_input = unwrap_maps_url(address)
    logger.warning("yandex resolve openai input address=%r input=%r", address, openai_input)
    print(f"yandex resolve openai input address={address!r} input={openai_input!r}", flush=True)
    response = client.responses.create(
        prompt={
            "id": YANDEX_MAPS_PROMPT_ID,
            "version": YANDEX_MAPS_PROMPT_VERSION,
        },
        input=openai_input,
    )
    yandex_url = response.output_text.strip()
    logger.warning("yandex resolve openai output address=%r output=%r", address, yandex_url)
    print(f"yandex resolve openai output address={address!r} output={yandex_url!r}", flush=True)
    ResolvedYandexAddress.objects.create(address=address, yandex_url=yandex_url)
    return yandex_url
