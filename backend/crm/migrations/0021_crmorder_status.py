from django.db import migrations, models


def fill_status(apps, schema_editor):
    CrmOrder = apps.get_model("crm", "CrmOrder")
    CrmOrder.objects.filter(is_delivered=True).update(status="delivered")
    CrmOrder.objects.filter(is_delivered=False, taken_by_id__isnull=False).update(status="in_work")


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0020_resolvedgoogleaddress"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "New"),
                    ("in_work", "In work"),
                    ("client_approved", "Client approved"),
                    ("in_delivery", "In delivery"),
                    ("delivered", "Delivered"),
                ],
                default="new",
                max_length=30,
            ),
        ),
        migrations.RunPython(fill_status, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="crmorder",
            name="is_delivered",
        ),
    ]
