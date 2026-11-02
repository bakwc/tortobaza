from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0070_cardsmsmessage_kind"),
    ]

    operations = [
        migrations.AlterField(
            model_name="crmorder",
            name="filling",
            field=models.CharField(blank=True, max_length=255, verbose_name="Filling"),
        ),
    ]
