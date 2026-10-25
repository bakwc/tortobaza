import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0065_crmorder_courier_alerted_departure_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnalyticsOrderComposition",
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
                ("source_hash", models.CharField(max_length=64, verbose_name="Source hash")),
                (
                    "parser",
                    models.CharField(
                        choices=[("rules", "Rules"), ("llm", "LLM")],
                        max_length=16,
                        verbose_name="Parser",
                    ),
                ),
                ("parsed_at", models.DateTimeField(auto_now=True, verbose_name="Parsed at")),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analytics_composition",
                        to="crm.crmorder",
                        verbose_name="Order",
                    ),
                ),
            ],
            options={
                "verbose_name": "Analytics order composition",
                "verbose_name_plural": "Analytics order compositions",
            },
        ),
        migrations.CreateModel(
            name="AnalyticsOrderCompositionItem",
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
                    "kind",
                    models.CharField(
                        choices=[
                            ("cake", "Cake"),
                            ("bento", "Bento"),
                            ("cupcake", "Cupcake"),
                            ("macaron", "Macaron"),
                            ("addon", "Addon"),
                            ("other", "Other"),
                        ],
                        max_length=16,
                        verbose_name="Kind",
                    ),
                ),
                ("name", models.CharField(max_length=255, verbose_name="Name")),
                ("quantity", models.PositiveIntegerField(verbose_name="Quantity")),
                (
                    "weight_kg",
                    models.DecimalField(
                        blank=True,
                        decimal_places=3,
                        max_digits=6,
                        null=True,
                        verbose_name="Weight, kg",
                    ),
                ),
                ("filling", models.CharField(blank=True, max_length=255, verbose_name="Filling")),
                (
                    "price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=10,
                        null=True,
                        verbose_name="Price",
                    ),
                ),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Position")),
                (
                    "composition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="crm.analyticsordercomposition",
                        verbose_name="Composition",
                    ),
                ),
            ],
            options={
                "verbose_name": "Analytics order composition item",
                "verbose_name_plural": "Analytics order composition items",
                "ordering": ["position", "id"],
            },
        ),
    ]
