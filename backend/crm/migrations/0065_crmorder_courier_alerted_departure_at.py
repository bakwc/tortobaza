from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0064_import_legacy_crm_orders"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="courier_alerted_departure_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Courier alerted departure at"),
        ),
    ]
