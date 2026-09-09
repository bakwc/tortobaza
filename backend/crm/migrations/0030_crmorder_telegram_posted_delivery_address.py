from django.db import migrations, models
from django.db.models import F


def backfill_telegram_posted_delivery_address(apps, schema_editor):
    CrmOrder = apps.get_model("crm", "CrmOrder")
    CrmOrder.objects.filter(telegram_message_id__isnull=False).update(
        telegram_posted_delivery_address=F("delivery_address")
    )


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0029_crmorder_created_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="telegram_posted_delivery_address",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.RunPython(
            backfill_telegram_posted_delivery_address,
            migrations.RunPython.noop,
        ),
    ]
