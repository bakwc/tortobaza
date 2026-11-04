from django.db import migrations, models


def copy_lead(apps, schema_editor):
    SocialMessage = apps.get_model("crm", "SocialMessage")
    for message in SocialMessage.objects.select_related("channel__network").iterator():
        lead = message.potential_lead
        if message.potential_lead is True and message.channel.network.slug != "telegram":
            lead = None
        message.lead = lead
        message.save(update_fields=["lead"])


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0076_socialmessage_location_socialmessage_topic"),
    ]

    operations = [
        migrations.AddField(
            model_name="socialmessage",
            name="lead",
            field=models.BooleanField(blank=True, null=True, verbose_name="Lead"),
        ),
        migrations.AddField(
            model_name="socialmessage",
            name="context",
            field=models.JSONField(blank=True, null=True, verbose_name="Context"),
        ),
        migrations.RunPython(copy_lead, migrations.RunPython.noop),
    ]
