from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0014_order_time_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="skip_late_alerts",
            field=models.BooleanField(default=False, verbose_name="Skip late alerts"),
        ),
    ]
