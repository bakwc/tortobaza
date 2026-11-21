from decimal import Decimal

import django.core.validators
from django.db import migrations, models


def copy_loss(apps, _schema_editor):
    hundred = Decimal("100")
    for model_name in ("SemiProductLine", "TechCardLine", "TechCardModifierLine"):
        model = apps.get_model("menu", model_name)
        for line in model.objects.all():
            percent = line.loss_percent
            quantity = line.quantity
            if quantity is None or percent == 0:
                loss = Decimal("0")
            else:
                loss = (quantity * percent / (hundred - percent)).quantize(Decimal("0.001"))
            line.loss_quantity = loss
            line.save(update_fields=["loss_quantity"])


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0024_techcardline_nested_section"),
    ]

    operations = [
        migrations.AddField(
            model_name="semiproductline",
            name="loss_quantity",
            field=models.DecimalField(
                decimal_places=3,
                default=Decimal("0"),
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                verbose_name="Loss",
            ),
        ),
        migrations.AddField(
            model_name="techcardline",
            name="loss_quantity",
            field=models.DecimalField(
                decimal_places=3,
                default=Decimal("0"),
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                verbose_name="Loss",
            ),
        ),
        migrations.AddField(
            model_name="techcardmodifierline",
            name="loss_quantity",
            field=models.DecimalField(
                decimal_places=3,
                default=Decimal("0"),
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                verbose_name="Loss",
            ),
        ),
        migrations.RunPython(copy_loss, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="semiproductline",
            name="loss_percent",
        ),
        migrations.RemoveField(
            model_name="techcardline",
            name="loss_percent",
        ),
        migrations.RemoveField(
            model_name="techcardmodifierline",
            name="loss_percent",
        ),
    ]
