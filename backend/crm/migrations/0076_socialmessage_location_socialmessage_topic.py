from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0075_social_network_messages"),
    ]

    operations = [
        migrations.AddField(
            model_name="socialmessage",
            name="location",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="Location"
            ),
        ),
        migrations.AddField(
            model_name="socialmessage",
            name="topic",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="Topic"
            ),
        ),
    ]
