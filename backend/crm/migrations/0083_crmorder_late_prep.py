from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0082_financialaccount_card_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="late_prep_closed",
            field=models.BooleanField(default=False, verbose_name="Late prep closed"),
        ),
        migrations.AddField(
            model_name="crmorder",
            name="late_prep_message_id",
            field=models.BigIntegerField(blank=True, null=True, verbose_name="Late prep message id"),
        ),
    ]
