from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rsge", "0004_reset_sync_dates"),
    ]

    operations = [
        migrations.AlterField(
            model_name="waybillgood",
            name="a_id",
            field=models.BigIntegerField(null=True, verbose_name="A id"),
        ),
    ]
