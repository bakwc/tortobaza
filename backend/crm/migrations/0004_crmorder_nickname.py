from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0003_crmorder_delivery_address"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="nickname",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
