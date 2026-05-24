from django.db import migrations, models


TIER_CHOICES = [
    ("all_day", "All day"),
    ("same_day", "Same day or later"),
    ("next_day", "Next day or later"),
    ("plus_2", "Two days or later"),
    ("plus_3", "Three days or later"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0008_backfill_default_language_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="category",
            name="delivery_schedule_tier",
            field=models.CharField(
                choices=TIER_CHOICES,
                default="same_day",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="delivery_schedule_tier",
            field=models.CharField(
                blank=True,
                choices=TIER_CHOICES,
                max_length=20,
                null=True,
            ),
        ),
    ]
