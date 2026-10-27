from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AuditEvent(models.Model):
    ACTION_CREATED = "created"
    ACTION_UPDATED = "updated"
    ACTION_DELETED = "deleted"
    ACTION_CHOICES = [
        (ACTION_CREATED, _("Created")),
        (ACTION_UPDATED, _("Updated")),
        (ACTION_DELETED, _("Deleted")),
    ]

    SOURCE_USER = "user"
    SOURCE_CRM = "crm"
    SOURCE_ADMIN = "admin"
    SOURCE_WEBSITE = "website"
    SOURCE_FLOWWOW = "flowwow"
    SOURCE_CHOICES = [
        (SOURCE_USER, _("User")),
        (SOURCE_CRM, _("CRM")),
        (SOURCE_ADMIN, _("Admin")),
        (SOURCE_WEBSITE, _("Website")),
        (SOURCE_FLOWWOW, _("Flowwow")),
    ]

    created_at = models.DateTimeField(default=timezone.now)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="audit_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    app_label = models.CharField(max_length=50)
    model = models.CharField(max_length=80)
    object_id = models.CharField(max_length=64)
    object_label = models.CharField(max_length=255)
    database = models.CharField(max_length=20)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    changes = models.JSONField()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["created_at"], name="audit_event_created_at"),
            models.Index(fields=["app_label", "model", "created_at"], name="audit_event_model_at"),
        ]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.app_label}.{self.model} {self.object_id}"
