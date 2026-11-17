from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0018_order_info_permissions"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userprofile",
            name="pushover_user",
        ),
        migrations.AddField(
            model_name="userprofile",
            name="bark_device_key",
            field=models.CharField(blank=True, max_length=128, verbose_name="Bark device key"),
        ),
    ]
