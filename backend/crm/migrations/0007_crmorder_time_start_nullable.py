from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0006_crmorder_deleted"),
    ]

    operations = [
        migrations.AlterField(
            model_name="crmorder",
            name="time_start",
            field=models.TimeField(blank=True, null=True),
        ),
    ]
