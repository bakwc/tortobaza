from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="is_delivered",
            field=models.BooleanField(default=False),
        ),
    ]
