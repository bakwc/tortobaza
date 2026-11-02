import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0071_crmorder_filling_blank"),
    ]

    operations = [
        migrations.CreateModel(
            name="TelegramChannel",
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
                ("username", models.CharField(max_length=255, unique=True, verbose_name="Username")),
                ("enabled", models.BooleanField(default=True, verbose_name="Enabled")),
                ("title", models.CharField(blank=True, default="", max_length=255, verbose_name="Title")),
                ("telegram_id", models.BigIntegerField(blank=True, null=True, verbose_name="Telegram ID")),
                ("last_message_id", models.BigIntegerField(default=0, verbose_name="Last message id")),
            ],
            options={
                "verbose_name": "Telegram channel",
                "verbose_name_plural": "Telegram channels",
                "ordering": ["username"],
            },
        ),
        migrations.CreateModel(
            name="TelegramChannelMessage",
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
                ("message_id", models.BigIntegerField(verbose_name="Message id")),
                ("sent_at", models.DateTimeField(verbose_name="Sent at")),
                ("text", models.TextField(blank=True, default="", verbose_name="Text")),
                ("sender_id", models.BigIntegerField(blank=True, null=True, verbose_name="Sender ID")),
                (
                    "sender_username",
                    models.CharField(blank=True, default="", max_length=32, verbose_name="Sender username"),
                ),
                (
                    "channel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="crm.telegramchannel",
                        verbose_name="Channel",
                    ),
                ),
            ],
            options={
                "verbose_name": "Telegram channel message",
                "verbose_name_plural": "Telegram channel messages",
                "ordering": ["-sent_at", "-message_id"],
            },
        ),
        migrations.AddConstraint(
            model_name="telegramchannelmessage",
            constraint=models.UniqueConstraint(
                fields=("channel", "message_id"),
                name="uniq_telegramchannelmessage_channel_message_id",
            ),
        ),
    ]
