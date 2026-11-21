import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("menu", "0025_loss_quantity"),
    ]

    operations = [
        migrations.CreateModel(
            name="TechCardDraft",
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
                ("client_id", models.UUIDField(unique=True, verbose_name="Client id")),
                ("name", models.TextField(blank=True, default="", verbose_name="Name")),
                ("payload", models.JSONField(verbose_name="Payload")),
                ("client_updated_at", models.DateTimeField(verbose_name="Client updated at")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated at")),
                (
                    "tech_card",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="drafts",
                        to="menu.techcard",
                        unique=True,
                        verbose_name="Tech card",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tech_card_drafts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Updated by",
                    ),
                ),
            ],
            options={
                "verbose_name": "Tech card draft",
                "verbose_name_plural": "Tech card drafts",
                "ordering": ["-client_updated_at"],
            },
        ),
    ]
