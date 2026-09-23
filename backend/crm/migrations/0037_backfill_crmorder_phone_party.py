from django.db import migrations

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
        ("crm", "0036_crmorder_phones"),
    ]

    operations = [
        migrations.RunPython(backfill_crm_order_phones, migrations.RunPython.noop),
    ]
