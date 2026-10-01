from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0040_crmorderevent"),
    ]

    operations = [
        migrations.CreateModel(
            name="TelegramNumberCheck",
            fields=[],
            options={
                "verbose_name": "Telegram number check",
                "verbose_name_plural": "Telegram number check",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("crm.crmorder",),
        ),
    ]
