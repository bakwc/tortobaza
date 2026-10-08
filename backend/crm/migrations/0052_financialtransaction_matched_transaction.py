from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0051_crmorder_payment_type_tbank"),
    ]

    operations = [
        migrations.AddField(
            model_name="financialtransaction",
            name="matched_transaction",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="+",
                to="crm.financialtransaction",
            ),
        ),
    ]
