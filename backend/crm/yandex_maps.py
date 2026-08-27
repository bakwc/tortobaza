from django.conf import settings
from openai import OpenAI

from crm.models import ResolvedYandexAddress

YANDEX_MAPS_PROMPT_ID = "pmpt_6a8fc1da64a8819492de6245ec4b8d5a008cb33b36bf3697"
YANDEX_MAPS_PROMPT_VERSION = "1"


def resolve_yandex_maps_url(address: str) -> str:
    cached = ResolvedYandexAddress.objects.filter(address=address).first()
    if cached:
        return cached.yandex_url
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.responses.create(
        prompt={
            "id": YANDEX_MAPS_PROMPT_ID,
            "version": YANDEX_MAPS_PROMPT_VERSION,
        },
        input=address,
    )
    yandex_url = response.output_text.strip()
    ResolvedYandexAddress.objects.create(address=address, yandex_url=yandex_url)
    return yandex_url
