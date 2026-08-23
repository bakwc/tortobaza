from django.db import migrations


def seed_birthday_cakes_landing(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    CategoryLanding = apps.get_model("catalog", "CategoryLanding")

    bento = Category.objects.filter(page_slug_en="bento-cakes").first()
    if not bento:
        bento = Category.objects.filter(slug="bento-cake").first()
    if not bento:
        return

    CategoryLanding.objects.update_or_create(
        slug="birthday-cakes",
        defaults={
            "source": bento,
            "page_slug_en": "birthday-cakes",
            "page_slug_ru": "torty-na-den-rozhdeniya",
            "page_slug_ka": "dabadebis-dgis-tortebi",
            "page_heading_en": "Birthday cakes in Batumi",
            "page_heading_ru": "Торты на день рождения в Батуми",
            "page_heading_ka": "დაბადების დღის ტორტები ბათუმში",
            "page_description_en": (
                "Personalized birthday cakes and bento in Batumi. Custom text and drawings, "
                "convenient portion sizes for small celebrations, and same-day delivery when ordered before 15:00."
            ),
            "page_description_ru": (
                "Авторские торты на день рождения и бенто в Батуми. Индивидуальные надписи и рисунки, "
                "удобный формат для праздника и доставка день в день при заказе до 15:00."
            ),
            "page_description_ka": (
                "დაბადების დღის ტორტები და ბენტო ბათუმში. ინდივიდუალური წარწერები და ნახატები, "
                "მოსახერხებელი პორციები და იმავე დღის მიწოდება 15:00-მდე შეკვეთისას."
            ),
            "seo_title_en": "Birthday cakes in Batumi",
            "seo_title_ru": "Торты на день рождения в Батуми",
            "seo_title_ka": "დაბადების დღის ტორტები ბათუმში",
            "seo_description_en": (
                "Order custom birthday cakes in Batumi from Sweet & Chill. "
                "Handcrafted bento cakes with personalized designs and same-day delivery."
            ),
            "seo_description_ru": (
                "Закажите торт на день рождения в Батуми в Sweet & Chill. "
                "Бенто-торты с индивидуальным декором и быстрой доставкой по городу."
            ),
            "seo_description_ka": (
                "შეუკვეთეთ დაბადების დღის ტორტები ბათუმში Sweet & Chill-დან. "
                "ხელნაკეთი ბენტო ტორტები ინდივიდუალური დიზაინით და სწრაფი მიწოდებით."
            ),
            "is_active": True,
        },
    )


def remove_birthday_cakes_landing(apps, schema_editor):
    CategoryLanding = apps.get_model("catalog", "CategoryLanding")
    CategoryLanding.objects.filter(slug="birthday-cakes").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0013_categorylanding"),
    ]

    operations = [
        migrations.RunPython(seed_birthday_cakes_landing, remove_birthday_cakes_landing),
    ]
