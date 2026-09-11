from decimal import Decimal

from django.db import migrations, models


def create_crm_settings(apps, schema_editor):
    CrmSettings = apps.get_model("crm", "CrmSettings")
    CrmSettings.objects.get_or_create(
        pk=1,
        defaults={"monthly_rent": Decimal("0.00")},
    )


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0030_crmorder_telegram_posted_delivery_address"),
    ]

    operations = [
        migrations.CreateModel(
            name="CrmSettings",
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
                    "monthly_rent",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                    ),
                ),
            ],
            options={
                "verbose_name": "CRM settings",
                "verbose_name_plural": "CRM settings",
            },
        ),
        migrations.RunPython(create_crm_settings, migrations.RunPython.noop),
    ]
