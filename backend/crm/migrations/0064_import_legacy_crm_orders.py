from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0063_rsge_document_links"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
