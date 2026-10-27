import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def copy_crm_order_events(apps, schema_editor):
    OrderEvent = apps.get_model("crm", "CrmOrderEvent")
    AuditEvent = apps.get_model("audit", "AuditEvent")
    batch = []
    for event in OrderEvent.objects.select_related("order").iterator(chunk_size=500):
        order = event.order
        batch.append(
            AuditEvent(
                created_at=event.created_at,
                actor_id=event.actor_id,
                action=event.action,
                app_label="crm",
                model="crmorder",
                object_id=str(event.order_id),
                object_label=f"{order.date} {order.contact}"[:255],
                database="default",
                source=event.source,
                changes=event.changes,
            )
        )
        if len(batch) == 500:
            AuditEvent.objects.using(schema_editor.connection.alias).bulk_create(batch)
            batch = []
    if batch:
        AuditEvent.objects.using(schema_editor.connection.alias).bulk_create(batch)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("crm", "0069_financialaccount_cards_cardsmsmessage"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("action", models.CharField(choices=[("created", "Created"), ("updated", "Updated"), ("deleted", "Deleted")], max_length=20)),
                ("app_label", models.CharField(max_length=50)),
                ("model", models.CharField(max_length=80)),
                ("object_id", models.CharField(max_length=64)),
                ("object_label", models.CharField(max_length=255)),
                ("database", models.CharField(max_length=20)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("user", "User"),
                            ("crm", "CRM"),
                            ("admin", "Admin"),
                            ("website", "Website"),
                            ("flowwow", "Flowwow"),
                        ],
                        max_length=20,
                    ),
                ),
                ("changes", models.JSONField()),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["created_at"], name="audit_event_created_at"),
                    models.Index(fields=["app_label", "model", "created_at"], name="audit_event_model_at"),
                ],
            },
        ),
        migrations.RunPython(copy_crm_order_events, migrations.RunPython.noop),
    ]
