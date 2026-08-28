import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0018_crmorder_midnight_last_ordering"),
        ("orders", "0011_order_environment"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="website_order",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="crm_order",
                to="orders.order",
            ),
        ),
    ]
