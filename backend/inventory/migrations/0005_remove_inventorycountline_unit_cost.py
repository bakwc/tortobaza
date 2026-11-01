from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_waybill_supply"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="inventorycountline",
            name="unit_cost",
        ),
    ]
