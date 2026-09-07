from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0027_clear_instagram_resolved_addresses"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="internal_description",
            field=models.TextField(blank=True),
        ),
    ]
