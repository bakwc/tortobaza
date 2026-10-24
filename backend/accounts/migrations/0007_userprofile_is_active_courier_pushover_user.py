from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_userprofile_can_login_monthly_rate"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="is_active_courier",
            field=models.BooleanField(default=False, verbose_name="Active courier"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="pushover_user",
            field=models.CharField(blank=True, max_length=30, verbose_name="Pushover user"),
        ),
    ]
