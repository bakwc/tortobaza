from django.db import migrations, models


def fill_quantity_unit(apps, schema_editor):
    for model_name in ("SemiProductLine", "TechCardLine", "TechCardModifierLine"):
        Line = apps.get_model("menu", model_name)
        for line in Line.objects.select_related("ingredient", "semi_product"):
            component = line.ingredient if line.ingredient_id is not None else line.semi_product
            line.quantity_unit = component.unit
            line.save(update_fields=["quantity_unit"])


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0008_ingredient_grams_per_unit"),
    ]

    operations = [
        migrations.AddField(
            model_name="semiproductline",
            name="quantity_unit",
            field=models.CharField(
                choices=[("g", "Gram"), ("ml", "Milliliter"), ("pcs", "Piece")],
                max_length=3,
                null=True,
                verbose_name="Quantity unit",
            ),
        ),
        migrations.AddField(
            model_name="techcardline",
            name="quantity_unit",
            field=models.CharField(
                choices=[("g", "Gram"), ("ml", "Milliliter"), ("pcs", "Piece")],
                max_length=3,
                null=True,
                verbose_name="Quantity unit",
            ),
        ),
        migrations.AddField(
            model_name="techcardmodifierline",
            name="quantity_unit",
            field=models.CharField(
                choices=[("g", "Gram"), ("ml", "Milliliter"), ("pcs", "Piece")],
                max_length=3,
                null=True,
                verbose_name="Quantity unit",
            ),
        ),
        migrations.RunPython(fill_quantity_unit, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="semiproductline",
            name="quantity_unit",
            field=models.CharField(
                choices=[("g", "Gram"), ("ml", "Milliliter"), ("pcs", "Piece")],
                max_length=3,
                verbose_name="Quantity unit",
            ),
        ),
        migrations.AlterField(
            model_name="techcardline",
            name="quantity_unit",
            field=models.CharField(
                choices=[("g", "Gram"), ("ml", "Milliliter"), ("pcs", "Piece")],
                max_length=3,
                verbose_name="Quantity unit",
            ),
        ),
        migrations.AlterField(
            model_name="techcardmodifierline",
            name="quantity_unit",
            field=models.CharField(
                choices=[("g", "Gram"), ("ml", "Milliliter"), ("pcs", "Piece")],
                max_length=3,
                verbose_name="Quantity unit",
            ),
        ),
    ]
