import django.core.validators
from django.db import migrations, models


def set_piece_basis(apps, schema_editor):
    TechCard = apps.get_model("menu", "TechCard")
    TechCard.objects.filter(kind="piece", basis_quantity__isnull=True).update(basis_quantity=1)


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0003_techcard_basis_method_images"),
    ]

    operations = [
        migrations.AddField(
            model_name="techcard",
            name="basis_quantity",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                validators=[django.core.validators.MinValueValidator(1)],
                verbose_name="Basis quantity",
            ),
        ),
        migrations.RunPython(set_piece_basis, migrations.RunPython.noop),
    ]
