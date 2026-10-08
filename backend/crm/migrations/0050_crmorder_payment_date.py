from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0049_financialtransaction_crm_orders"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="payment_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
