from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0031_crmsettings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="crmorder",
            name="status",
            field=models.CharField(
                choices=[
                    ("unconfirmed", "Unconfirmed"),
                    ("new", "New"),
                    ("in_work", "In work"),
                    ("client_approved", "Client approved"),
                    ("in_delivery", "In delivery"),
                    ("delivered", "Delivered"),
                ],
                default="new",
                max_length=30,
            ),
        ),
    ]
