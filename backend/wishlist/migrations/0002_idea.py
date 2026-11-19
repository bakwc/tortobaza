from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wishlist", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Idea",
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
                ("priority", models.PositiveIntegerField(verbose_name="Priority")),
                ("problem", models.TextField(blank=True, default="", verbose_name="Problem")),
                ("description", models.TextField(verbose_name="Description")),
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
                (
                    "duration",
                    models.DurationField(blank=True, null=True, verbose_name="Duration"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("doing", "Doing now"),
                            ("planned", "Will do"),
                            ("unknown", "Unknown"),
                            ("rejected", "Will not do"),
                            ("succeeded", "Checked, took off"),
                            ("failed", "Checked, did not take off"),
                        ],
                        default="unknown",
                        max_length=16,
                        verbose_name="Status",
                    ),
                ),
            ],
            options={
                "verbose_name": "Idea",
                "verbose_name_plural": "Ideas",
            },
        ),
    ]
