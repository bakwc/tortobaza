from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0085_crmorder_telegram_posted_items"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="crmorder",
            name="courier_alerted_departure_at",
        ),
    ]
