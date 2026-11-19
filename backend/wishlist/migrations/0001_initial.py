from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="WishlistItem",
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
                ("title", models.CharField(max_length=200, verbose_name="Title")),
                ("purpose", models.TextField(blank=True, default="", verbose_name="Purpose")),
                ("priority", models.PositiveIntegerField(verbose_name="Priority")),
                (
                    "cost",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=12,
                        null=True,
                        verbose_name="Cost",
                    ),
                ),
            ],
            options={
                "verbose_name": "Wishlist item",
                "verbose_name_plural": "Wishlist items",
                "ordering": ["priority", "id"],
            },
        ),
    ]
