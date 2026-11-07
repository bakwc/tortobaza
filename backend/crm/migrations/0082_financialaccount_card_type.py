from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0081_lead_verticals"),
    ]

    operations = [
        migrations.AddField(
            model_name="financialaccount",
            name="card_type",
            field=models.CharField(blank=True, default="", max_length=64, verbose_name="Card type"),
        ),
    ]
