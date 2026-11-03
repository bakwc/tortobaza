from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0072_telegramchannel_telegramchannelmessage"),
    ]

    operations = [
        migrations.CreateModel(
            name="TelegramKeyword",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("word", models.CharField(max_length=255, unique=True, verbose_name="Word")),
            ],
            options={
                "verbose_name": "Telegram keyword",
                "verbose_name_plural": "Telegram keywords",
                "ordering": ["word"],
            },
        ),
        migrations.AddField(
            model_name="telegramchannelmessage",
            name="keyword_match",
            field=models.BooleanField(default=False, verbose_name="Keyword match"),
        ),
        migrations.AddField(
            model_name="telegramchannelmessage",
            name="potential_lead",
            field=models.BooleanField(blank=True, null=True, verbose_name="Potential lead"),
        ),
    ]
