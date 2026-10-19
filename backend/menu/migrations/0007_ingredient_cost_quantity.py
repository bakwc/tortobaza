from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0006_techcardsection"),
    ]

    operations = [
        migrations.AddField(
            model_name="ingredient",
            name="cost_quantity",
            field=models.DecimalField(
                decimal_places=3,
                default=Decimal("1"),
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal("0.001"))],
                verbose_name="Cost quantity",
            ),
        ),
    ]
