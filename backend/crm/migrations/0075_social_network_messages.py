import django.db.models.deletion
from django.db import migrations, models


def seed_telegram_network(apps, schema_editor):
    SocialNetwork = apps.get_model("crm", "SocialNetwork")
    SocialNetwork.objects.create(slug="telegram", name="Telegram")


def attach_telegram_network(apps, schema_editor):
    SocialNetwork = apps.get_model("crm", "SocialNetwork")
    TelegramChannel = apps.get_model("crm", "TelegramChannel")
    network = SocialNetwork.objects.get(slug="telegram")
    TelegramChannel.objects.all().update(network_id=network.id)


def backfill_message_identity(apps, schema_editor):
    SocialMessage = apps.get_model("crm", "SocialMessage")
    for message in SocialMessage.objects.select_related("channel").iterator():
        message.external_id = str(message.message_id)
        message.url = f"https://t.me/{message.channel.username}/{message.message_id}"
        message.save(update_fields=["external_id", "url"])


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0074_telegramchannelmessage_lead_notified"),
    ]

    operations = [
        migrations.CreateModel(
            name="SocialNetwork",
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
                ("slug", models.SlugField(max_length=64, unique=True, verbose_name="Slug")),
                ("name", models.CharField(max_length=255, verbose_name="Name")),
            ],
            options={
                "verbose_name": "Social network",
                "verbose_name_plural": "Social networks",
                "ordering": ["name"],
            },
        ),
        migrations.RunPython(seed_telegram_network, migrations.RunPython.noop),
        migrations.AddField(
            model_name="telegramchannel",
            name="network",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sources",
                to="crm.socialnetwork",
                verbose_name="Network",
            ),
        ),
        migrations.RunPython(attach_telegram_network, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="telegramchannel",
            name="network",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sources",
                to="crm.socialnetwork",
                verbose_name="Network",
            ),
        ),
        migrations.AlterField(
            model_name="telegramchannel",
            name="username",
            field=models.CharField(max_length=255, verbose_name="Username"),
        ),
        migrations.AddConstraint(
            model_name="telegramchannel",
            constraint=models.UniqueConstraint(
                fields=("network", "username"),
                name="uniq_socialsource_network_username",
            ),
        ),
        migrations.RenameModel(old_name="TelegramChannel", new_name="SocialSource"),
        migrations.AlterModelOptions(
            name="socialsource",
            options={
                "verbose_name": "Social source",
                "verbose_name_plural": "Social sources",
                "ordering": ["username"],
            },
        ),
        migrations.RenameModel(old_name="TelegramKeyword", new_name="SocialKeyword"),
        migrations.AlterModelOptions(
            name="socialkeyword",
            options={
                "verbose_name": "Social keyword",
                "verbose_name_plural": "Social keywords",
                "ordering": ["word"],
            },
        ),
        migrations.RenameModel(old_name="TelegramChannelMessage", new_name="SocialMessage"),
        migrations.AddField(
            model_name="socialmessage",
            name="external_id",
            field=models.CharField(default="", max_length=255, verbose_name="External id"),
        ),
        migrations.AddField(
            model_name="socialmessage",
            name="url",
            field=models.CharField(default="", max_length=2048, verbose_name="URL"),
        ),
        migrations.AlterField(
            model_name="socialmessage",
            name="sender_id",
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="Sender ID"),
        ),
        migrations.AlterField(
            model_name="socialmessage",
            name="sender_username",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Sender username"),
        ),
        migrations.RunPython(backfill_message_identity, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="socialmessage",
            name="uniq_telegramchannelmessage_channel_message_id",
        ),
        migrations.RemoveField(
            model_name="socialmessage",
            name="message_id",
        ),
        migrations.AlterField(
            model_name="socialmessage",
            name="external_id",
            field=models.CharField(max_length=255, verbose_name="External id"),
        ),
        migrations.AlterField(
            model_name="socialmessage",
            name="url",
            field=models.CharField(max_length=2048, verbose_name="URL"),
        ),
        migrations.AddConstraint(
            model_name="socialmessage",
            constraint=models.UniqueConstraint(
                fields=("channel", "external_id"),
                name="uniq_socialmessage_channel_external_id",
            ),
        ),
        migrations.AlterModelOptions(
            name="socialmessage",
            options={
                "verbose_name": "Social message",
                "verbose_name_plural": "Social messages",
                "ordering": ["-sent_at", "-external_id"],
            },
        ),
    ]
