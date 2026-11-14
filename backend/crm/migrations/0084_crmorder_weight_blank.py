from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0083_crmorder_late_prep"),
    ]

    operations = [
        migrations.AlterField(
            model_name="crmorder",
            name="weight",
            field=models.CharField(blank=True, max_length=50, verbose_name="Weight"),
        ),
    ]
