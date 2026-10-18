from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0019_product_tech_card"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="delivery_price",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                max_digits=10,
                verbose_name="Delivery",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="base_price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                verbose_name="Price (without delivery)",
            ),
        ),
    ]
