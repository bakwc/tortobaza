from django.db import migrations


def seed_cakes_to_order_landing(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    CategoryLanding = apps.get_model("catalog", "CategoryLanding")

    bento = Category.objects.filter(page_slug_en="bento-cakes").first()
    if not bento:
        bento = Category.objects.filter(slug="bento-cake").first()
    if not bento:
        return

    CategoryLanding.objects.update_or_create(
        slug="cakes-to-order",
        defaults={
            "source": bento,
            "page_slug_en": "cakes-to-order",
            "page_slug_ru": "torty-na-zakaz",
            "page_slug_ka": "tortebi-shekvetit",
            "page_heading_en": "Cakes to order in Batumi",
            "page_heading_ru": "Торты на заказ в Батуми",
            "page_heading_ka": "ტორტები შეკვეთით ბათუმში",
            "page_description_en": (
                "Cakes to order in Batumi from Sweet & Chill. "
                "Handcrafted bento cakes with custom designs and lettering, "
                "fresh ingredients, and delivery across the city, including same-day when ordered before 15:00."
            ),
            "page_description_ru": (
                "Торты на заказ в Батуми от кондитерской Sweet & Chill. "
                "Авторские бенто-торты с индивидуальным декором и надписями, "
                "свежие ингредиенты и доставка по городу, в том числе день в день при заказе до 15:00."
            ),
            "page_description_ka": (
                "ტორტები შეკვეთით ბათუმში Sweet & Chill-ისგან. "
                "ხელნაკეთი ბენტო ტორტები ინდივიდუალური დიზაინით და წარწერებით, "
                "ახალი ინგრედიენტები და მიწოდება ქალაქში, მათ შორის იმავე დღეს 15:00-მდე შეკვეთისას."
            ),
            "seo_title_en": "Cakes to order in Batumi",
            "seo_title_ru": "Торты на заказ в Батуми",
            "seo_title_ka": "ტორტები შეკვეთით ბათუმში",
            "seo_description_en": (
                "Order custom cakes in Batumi from Sweet & Chill. "
                "Handmade cakes to order with personalized designs and delivery across the city."
            ),
            "seo_description_ru": (
                "Закажите торты на заказ в Батуми в Sweet & Chill. "
                "Изготовление авторских тортов с индивидуальным декором и доставкой по городу."
            ),
            "seo_description_ka": (
                "შეუკვეთეთ ტორტები შეკვეთით ბათუმში Sweet & Chill-ში. "
                "ავტორული ტორტების დამზადება ინდივიდუალური დეკორით და მიწოდებით ქალაქში."
            ),
            "is_active": True,
        },
    )


def remove_cakes_to_order_landing(apps, schema_editor):
    CategoryLanding = apps.get_model("catalog", "CategoryLanding")
    CategoryLanding.objects.filter(slug="cakes-to-order").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0015_seed_urgent_cakes_landing"),
    ]

    operations = [
        migrations.RunPython(seed_cakes_to_order_landing, remove_cakes_to_order_landing),
    ]
