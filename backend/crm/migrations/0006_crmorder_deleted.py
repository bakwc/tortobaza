from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0005_crmorder_payment_type_unknown"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
    ]
