from xml.etree import ElementTree as ET

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from catalog.models import Product

G_NS = "http://base.google.com/ns/1.0"
G = f"{{{G_NS}}}"
ET.register_namespace("g", G_NS)

DESCR_LIMIT = 5000
ADDTL_IMAGE_LIMIT = 10


def _image_link(rel: str, public_base_url: str) -> str:
    rel_clean = rel.lstrip("/")
    base = f"{public_base_url.rstrip('/')}/api/img/{rel_clean}"
    return f"{base}?w=1200"


def _feed_description(product: Product) -> str:
    raw = product.description.strip() if product.description else product.name
    if len(raw) > DESCR_LIMIT:
        return raw[:DESCR_LIMIT]
    return raw


@cache_page(60 * 30)
@vary_on_headers("Host")
def meta_product_feed(request) -> HttpResponse:
    rss = ET.Element("rss")
    rss.set("version", "2.0")

    channel = ET.SubElement(rss, "channel")
    base_url = request.build_absolute_uri("/").rstrip("/")

    ET.SubElement(channel, "title").text = settings.META_FEED_BRAND
    ET.SubElement(channel, "link").text = base_url
    ET.SubElement(channel, "description").text = settings.META_FEED_BRAND

    qs = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("images")
    )

    for product in qs:
        images = sorted(product.images.all(), key=lambda im: (im.position, im.pk))
        if not images:
            continue

        item = ET.SubElement(channel, "item")
        ET.SubElement(item, f"{G}id").text = str(product.id)
        ET.SubElement(item, f"{G}title").text = product.name
        ET.SubElement(item, f"{G}description").text = _feed_description(product)
        ET.SubElement(item, f"{G}link").text = f"{base_url}/order/{product.slug}"
        ET.SubElement(item, f"{G}image_link").text = _image_link(images[0].image.name, base_url)

        for img in images[1 : 1 + ADDTL_IMAGE_LIMIT]:
            ET.SubElement(item, f"{G}additional_image_link").text = _image_link(img.image.name, base_url)

        ET.SubElement(item, f"{G}availability").text = "in stock"
        ET.SubElement(item, f"{G}condition").text = "new"
        ET.SubElement(item, f"{G}price").text = f"{product.base_price:.2f} GEL"
        ET.SubElement(item, f"{G}brand").text = settings.META_FEED_BRAND
        ET.SubElement(item, f"{G}product_type").text = product.category.name
        ET.SubElement(item, f"{G}google_product_category").text = product.category.name
        ET.SubElement(item, f"{G}identifier_exists").text = "no"

    body = ET.tostring(rss, encoding="utf-8", xml_declaration=True)
    return HttpResponse(body, content_type="application/xml; charset=utf-8")
