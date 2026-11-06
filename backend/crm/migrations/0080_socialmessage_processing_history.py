from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0079_crmorderitemline_tech_card"),
    ]

    operations = [
        migrations.AddField(
            model_name="socialmessage",
            name="processing_history",
            field=models.JSONField(default=list, verbose_name="Processing history"),
        ),
    ]
