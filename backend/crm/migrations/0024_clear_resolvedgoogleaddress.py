from django.db import migrations


def clear_resolved_google_addresses(apps, schema_editor):
    ResolvedGoogleAddress = apps.get_model("crm", "ResolvedGoogleAddress")
    ResolvedGoogleAddress.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0023_alter_crmorder_client_token"),
    ]

    operations = [
        migrations.RunPython(clear_resolved_google_addresses, migrations.RunPython.noop),
    ]
