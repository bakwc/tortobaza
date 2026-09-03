import secrets

from django.db import migrations, models


def generate_crm_client_token():
    return secrets.token_hex(32)


def fill_client_tokens(apps, schema_editor):
    CrmOrder = apps.get_model("crm", "CrmOrder")
    for order in CrmOrder.objects.all().iterator():
        order.client_token = secrets.token_hex(32)
        order.save(update_fields=["client_token"])


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0021_crmorder_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="client_token",
            field=models.CharField(default="", max_length=64),
        ),
        migrations.RunPython(fill_client_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="crmorder",
            name="client_token",
            field=models.CharField(
                db_index=True,
                default=generate_crm_client_token,
                editable=False,
                max_length=64,
                unique=True,
            ),
        ),
    ]
