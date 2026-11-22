from django.db import migrations, models


def copy_option_modifiers(apps, schema_editor):
    Modifier = apps.get_model("menu", "Modifier")
    Option = apps.get_model("catalog", "Option")
    through = Option.modifiers.through
    through.objects.bulk_create(
        [
            through(option_id=modifier.catalog_option_id, modifier_id=modifier.id)
            for modifier in Modifier.objects.exclude(catalog_option_id=None)
        ]
    )


def clear_option_modifiers(apps, schema_editor):
    Option = apps.get_model("catalog", "Option")
    Option.modifiers.through.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0022_image_crop"),
        ("menu", "0026_techcarddraft"),
    ]

    operations = [
        migrations.AddField(
            model_name="option",
            name="modifiers",
            field=models.ManyToManyField(
                blank=True,
                related_name="catalog_options",
                to="menu.modifier",
                verbose_name="Modifiers",
            ),
        ),
        migrations.RunPython(copy_option_modifiers, clear_option_modifiers),
    ]
