import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0087_socialmessage_text_folded"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="ready_photos_posted",
            field=models.BooleanField(default=False, verbose_name="Ready photos posted"),
        ),
        migrations.CreateModel(
            name="CrmOrderReadyImage",
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
                ("image", models.ImageField(upload_to="crm_order_ready/", verbose_name="Image")),
                (
                    "position",
                    models.PositiveIntegerField(default=0, verbose_name="Position"),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ready_images",
                        to="crm.crmorder",
                        verbose_name="Order",
                    ),
                ),
            ],
            options={
                "verbose_name": "CRM order ready image",
                "verbose_name_plural": "CRM order ready images",
                "ordering": ["position", "id"],
            },
        ),
    ]
