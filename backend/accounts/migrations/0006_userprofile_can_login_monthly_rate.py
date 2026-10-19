from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_userprofile_is_finance_admin"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="can_login",
            field=models.BooleanField(default=True, verbose_name="Can log in"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="monthly_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=10,
                verbose_name="Monthly rate",
            ),
        ),
    ]
