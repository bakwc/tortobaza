from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0061_crmorder_delivery_price"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="is_gift",
            field=models.BooleanField(default=False, verbose_name="Gift"),
        ),
    ]
