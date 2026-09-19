from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0033_crmorder_status_ready"),
    ]

    operations = [
        migrations.CreateModel(
            name="FlowwowWebhookEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("uuid", models.CharField(max_length=36, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
