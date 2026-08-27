from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0010_yandexaddressresolvefailure"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="when_ready",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="crmorder",
            name="telegram_posted_when_ready",
            field=models.BooleanField(default=False),
        ),
    ]
