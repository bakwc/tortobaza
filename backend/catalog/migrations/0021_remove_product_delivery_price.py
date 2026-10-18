from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0020_product_delivery_price"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="product",
            name="delivery_price",
        ),
        migrations.AlterField(
            model_name="product",
            name="base_price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                verbose_name="Base price",
            ),
        ),
    ]
