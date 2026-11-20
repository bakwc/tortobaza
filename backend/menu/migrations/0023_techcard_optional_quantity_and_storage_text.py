from django.db import migrations, models


def storage_temperature_text(apps, schema_editor):
    TechCard = apps.get_model("menu", "TechCard")
    for card in TechCard.objects.exclude(storage_temperature=None):
        value = str(card.storage_temperature)
        if value.lstrip("-").isdigit():
            card.storage_temperature = f"{value} °C"
            card.save(update_fields=["storage_temperature"])


def storage_temperature_number(apps, schema_editor):
    TechCard = apps.get_model("menu", "TechCard")
    suffix = " °C"
    for card in TechCard.objects.exclude(storage_temperature=None):
        value = str(card.storage_temperature)
        number = value[: -len(suffix)] if value.endswith(suffix) else value
        if number.lstrip("-").isdigit():
            card.storage_temperature = number
            card.save(update_fields=["storage_temperature"])


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0022_modifiergroup_priority"),
    ]

    operations = [
        migrations.AlterField(
            model_name="techcardline",
            name="quantity",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                max_digits=12,
                null=True,
                verbose_name="Quantity",
            ),
        ),
        migrations.AlterField(
            model_name="techcardmodifierline",
            name="quantity",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                max_digits=12,
                null=True,
                verbose_name="Quantity",
            ),
        ),
        migrations.AlterField(
            model_name="techcard",
            name="storage_temperature",
            field=models.CharField(
                blank=True,
                max_length=200,
                null=True,
                verbose_name="Storage temperature",
            ),
        ),
        migrations.RunPython(storage_temperature_text, storage_temperature_number),
    ]
