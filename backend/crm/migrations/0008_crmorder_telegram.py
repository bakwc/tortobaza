from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0007_crmorder_time_start_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="telegram_media_ids",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="crmorder",
            name="telegram_message_id",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="crmorder",
            name="telegram_payload_hash",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="crmorder",
            name="telegram_posted_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="crmorder",
            name="telegram_posted_time_end",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="crmorder",
            name="telegram_posted_time_start",
            field=models.TimeField(blank=True, null=True),
        ),
    ]
