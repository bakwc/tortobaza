from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0012_crmorder_payment_type_flowwow"),
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
                    ("flowwow", "Flowwow"),
                    ("crypto", "Cryptocurrency"),
                ],
                default="unknown",
                max_length=20,
            ),
        ),
    ]
