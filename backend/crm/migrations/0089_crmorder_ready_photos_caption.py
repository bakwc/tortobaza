from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0088_crmorderreadyimage"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="ready_photos_approved",
            field=models.BooleanField(default=False, verbose_name="Ready photos approved"),
        ),
        migrations.AddField(
            model_name="crmorder",
            name="ready_photos_message_id",
            field=models.BigIntegerField(blank=True, null=True, verbose_name="Ready photos message id"),
        ),
    ]
