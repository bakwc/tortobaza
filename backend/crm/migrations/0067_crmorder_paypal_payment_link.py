from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0066_analyticsordercomposition_analyticsordercompositionitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="paypal_link_id",
            field=models.CharField(blank=True, default="", max_length=50, verbose_name="PayPal link id"),
        ),
        migrations.AddField(
            model_name="crmorder",
            name="paypal_payment_url",
            field=models.CharField(blank=True, default="", max_length=500, verbose_name="PayPal payment URL"),
        ),
        migrations.AddField(
            model_name="crmorder",
            name="paypal_amount_usd",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                verbose_name="PayPal amount USD",
            ),
        ),
    ]
