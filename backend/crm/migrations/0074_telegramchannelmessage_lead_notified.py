from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0073_telegramkeyword_telegramchannelmessage_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="telegramchannelmessage",
            name="lead_notified",
            field=models.BooleanField(default=False, verbose_name="Lead notified"),
        ),
    ]
