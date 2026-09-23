from django.db import migrations, models

from crm.phone import phones_from_fields


def backfill_crm_order_phones(apps, schema_editor):
    CrmOrder = apps.get_model("crm", "CrmOrder")
    for order in CrmOrder.objects.iterator():
        phones = phones_from_fields(order.contact, order.nickname)
        if phones == order.phones:
            continue
        order.phones = phones
        order.save(update_fields=["phones"])


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0035_crmorder_flowwow_order_id_crmorderimage_source_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="phones",
            field=models.JSONField(default=list),
        ),
        migrations.RunPython(backfill_crm_order_phones, migrations.RunPython.noop),
    ]
