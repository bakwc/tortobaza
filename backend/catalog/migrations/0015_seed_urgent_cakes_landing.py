from django.db import migrations


def seed_urgent_cakes_landing(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    CategoryLanding = apps.get_model("catalog", "CategoryLanding")

    bento = Category.objects.filter(page_slug_en="bento-cakes").first()
    if not bento:
        bento = Category.objects.filter(slug="bento-cake").first()
    if not bento:
        return

    CategoryLanding.objects.update_or_create(
        slug="urgent-cakes",
        defaults={
            "source": bento,
            "page_slug_en": "urgent-cakes",
            "page_slug_ru": "srochnye-torty",
            "page_slug_ka": "saswrapfo-tortebi",
            "page_heading_en": "Urgent cakes in Batumi",
            "page_heading_ru": "Срочные торты в Батуми",
            "page_heading_ka": "სასწრაფო ტორტები ბათუმში",
            "page_description_en": (
                "Urgent handcrafted cakes and bento in Batumi. "
                "Freshly made to order with custom designs, lettering, and same-day delivery when ordered before 15:00."
            ),
            "page_description_ru": (
                "Срочное изготовление тортов и бенто на заказ в Батуми. "
                "Индивидуальный декор и надписи, свежие ингредиенты и доставка день в день при заказе до 15:00."
            ),
            "page_description_ka": (
                "სასწრაფო ტორტები და ბენტო შეკვეთით ბათუმში. "
                "ინდივიდუალური დიზაინი და წარწერები, ახალი ინგრედიენტები და იმავე დღის მიწოდება 15:00-მდე შეკვეთისას."
            ),
            "seo_title_en": "Urgent cakes in Batumi — same-day cake delivery",
            "seo_title_ru": "Срочные торты в Батуми — заказ торта день в день",
            "seo_title_ka": "სასწრაფო ტორტები ბათუმში — შეკვეთა იმავე დღეს",
            "seo_description_en": (
                "Order urgent cakes in Batumi with same-day delivery from Sweet & Chill. "
                "Custom bento cakes and personalized desserts made to order today."
            ),
            "seo_description_ru": (
                "Закажите срочный торт в Батуми с доставкой день в день от кондитерской Sweet & Chill. "
                "Изготовление бенто-тортов на заказ сегодня."
            ),
            "seo_description_ka": (
                "შეუკვეთეთ სასწრაფო ტორტი ბათუმში იმავე დღის მიწოდებით Sweet & Chill-ისგან. "
                "ბენტო ტორტების დამზადება შეკვეთით დღესვე."
            ),
            "is_active": True,
        },
    )


def remove_urgent_cakes_landing(apps, schema_editor):
    CategoryLanding = apps.get_model("catalog", "CategoryLanding")
    CategoryLanding.objects.filter(slug="urgent-cakes").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0014_seed_birthday_cakes_landing"),
    ]

    operations = [
        migrations.RunPython(seed_urgent_cakes_landing, remove_urgent_cakes_landing),
    ]
