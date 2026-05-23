from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_alter_optiongroup_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="delivery_schedule_tier",
            field=models.CharField(
                choices=[
                    ("same_day", "Same day or later"),
                    ("next_day", "Next day or later"),
                    ("plus_2", "Two days or later"),
                    ("plus_3", "Three days or later"),
                ],
                default="same_day",
                max_length=20,
            ),
        ),
    ]
