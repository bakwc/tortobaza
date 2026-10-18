from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0060_crmorderitem_crmorderitemmodifier_crmorderitemline"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="delivery_price",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                verbose_name="Delivery price",
            ),
        ),
    ]
