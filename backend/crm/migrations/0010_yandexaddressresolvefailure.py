from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0009_resolvedyandexaddress"),
    ]

    operations = [
        migrations.CreateModel(
            name="YandexAddressResolveFailure",
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
                ("address", models.TextField(unique=True)),
                ("failure_count", models.PositiveSmallIntegerField()),
            ],
        ),
    ]
