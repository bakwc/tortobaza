from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0007_ingredient_cost_quantity"),
    ]

    operations = [
        migrations.AddField(
            model_name="ingredient",
            name="grams_per_unit",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                max_digits=12,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.001"))],
                verbose_name="Grams per unit",
            ),
        ),
    ]
