from django.db import migrations


def reset_sync_dates(apps, schema_editor):
    WaybillSync = apps.get_model("rsge", "WaybillSync")
    InvoiceSync = apps.get_model("rsge", "InvoiceSync")
    WaybillSync.objects.all().delete()
    InvoiceSync.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rsge", "0003_waybill_invoice_ru_fields"),
    ]

    operations = [
        migrations.RunPython(reset_sync_dates, migrations.RunPython.noop),
    ]
