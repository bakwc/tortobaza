from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0011_order_environment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="customer_email",
            field=models.EmailField(max_length=254),
        ),
    ]
