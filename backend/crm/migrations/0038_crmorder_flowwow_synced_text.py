from django.db import migrations, models
from django.db.models import F


def backfill_flowwow_synced_text(apps, schema_editor):
    CrmOrder = apps.get_model("crm", "CrmOrder")
    CrmOrder.objects.exclude(flowwow_order_id=None).update(
        flowwow_synced_description=F("description"),
        flowwow_synced_internal_description=F("internal_description"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0037_backfill_crmorder_phone_party"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="flowwow_synced_description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="crmorder",
            name="flowwow_synced_internal_description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.RunPython(backfill_flowwow_synced_text, migrations.RunPython.noop),
    ]
