from datetime import datetime

from django.db import models, transaction

from audit.context import current_actor, database_of
from audit.models import AuditEvent
from audit.snapshot import child_changes, field_changes, object_label, snapshot_children, snapshot_fields
from audit.tracking import child_relations
from crm.models import CrmOrderEvent


def write_event(
    actor_id: int | None,
    action: str,
    app_label: str,
    model: str,
    object_id: str,
    object_label_value: str,
    database: str,
    source: str,
    changes: dict,
    created_at: datetime | None,
) -> AuditEvent:
    fields = {
        "actor_id": actor_id,
        "action": action,
        "app_label": app_label,
        "model": model,
        "object_id": object_id,
        "object_label": object_label_value,
        "database": database,
        "source": source,
        "changes": changes,
    }
    if created_at is not None:
        fields["created_at"] = created_at
    return AuditEvent.objects.using("default").create(**fields)


def enqueue(instance: models.Model, action: str, changes: dict) -> None:
    actor = current_actor()
    if actor is None:
        return
    if action != AuditEvent.ACTION_DELETED and not changes:
        return
    database = database_of(instance)
    payload = {
        "actor_id": actor.pk,
        "action": action,
        "app_label": instance._meta.app_label,
        "model": instance._meta.model_name,
        "object_id": str(instance.pk),
        "object_label_value": object_label(instance),
        "database": database,
        "source": AuditEvent.SOURCE_USER,
        "changes": changes,
        "created_at": None,
    }
    transaction.on_commit(lambda payload=payload: write_event(**payload), using=database)


def record_created(instances: list[models.Model]) -> None:
    if current_actor() is None:
        return
    for instance in instances:
        changes = field_changes(None, snapshot_fields(instance), AuditEvent.ACTION_CREATED)
        changes.update(
            child_changes({}, snapshot_children(instance, child_relations(type(instance))), AuditEvent.ACTION_CREATED)
        )
        enqueue(instance, AuditEvent.ACTION_CREATED, changes)


def record_updates(rows: list[tuple[models.Model, dict]]) -> None:
    if current_actor() is None:
        return
    for instance, before in rows:
        after = snapshot_fields(instance)
        changes = field_changes(before, after, AuditEvent.ACTION_UPDATED)
        if not changes:
            continue
        enqueue(instance, AuditEvent.ACTION_UPDATED, changes)


def mirror_order_event(event: CrmOrderEvent) -> None:
    order = event.order
    write_event(
        event.actor_id,
        event.action,
        "crm",
        "crmorder",
        str(order.pk),
        object_label(order),
        database_of(order),
        event.source,
        event.changes,
        event.created_at,
    )
