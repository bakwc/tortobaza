from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0050_crmorder_payment_date"),
    ]

    operations = [
        migrations.AlterField(
            model_name="crmorder",
            name="payment_type",
            field=models.CharField(
                choices=[
                    ("unknown", "Unknown"),
                    ("cash", "Cash"),
                    ("terminal", "Terminal"),
                    ("tbc", "TBC Transfer"),
                    ("bog", "BOG Transfer"),
                    ("tbank", "T-Bank Transfer"),
                    ("flowwow", "Flowwow"),
                    ("crypto", "Cryptocurrency"),
                    ("online", "Online on website"),
                ],
                default="unknown",
                max_length=20,
            ),
        ),
    ]
