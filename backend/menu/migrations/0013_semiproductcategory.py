import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0012_techcard_sale_price_per_piece"),
    ]

    operations = [
        migrations.CreateModel(
            name="SemiProductCategory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=120, unique=True, verbose_name="Name"),
                ),
                (
                    "position",
                    models.PositiveIntegerField(default=0, verbose_name="Position"),
                ),
            ],
            options={
                "verbose_name": "Semi-product category",
                "verbose_name_plural": "Semi-product categories",
                "ordering": ["position", "name"],
            },
        ),
        migrations.AddField(
            model_name="semiproduct",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="semi_products",
                to="menu.semiproductcategory",
                verbose_name="Category",
            ),
        ),
    ]
