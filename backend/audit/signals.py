from django.apps import apps
from django.db import transaction
from django.db.models.signals import post_save, pre_delete, pre_save

from audit.context import current_actor, database_of, pending_bucket
from audit.models import AuditEvent
from audit.record import write_event
from audit.snapshot import child_changes, field_changes, object_label, snapshot_children, snapshot_fields
from audit.tracking import child_relations, is_tracked

_connected = False


def connect() -> None:
    global _connected
    if _connected:
        return
    _connected = True
    pre_save.connect(on_pre_save)
    post_save.connect(on_post_save)
    pre_delete.connect(on_pre_delete)


def _key(instance) -> tuple[str, str, str, str]:
    return (database_of(instance), instance._meta.app_label, instance._meta.model_name, str(instance.pk))


def _entry(instance) -> dict:
    bucket = pending_bucket()
    key = _key(instance)
    entry = bucket.get(key)
    if entry is None:
        entry = {
            "created": False,
            "before_fields": None,
            "before_children": None,
            "deleted": None,
            "scheduled": False,
            "actor_id": current_actor().pk,
            "pk": instance.pk,
            "app_label": instance._meta.app_label,
            "model": instance._meta.model_name,
            "database": database_of(instance),
        }
        bucket[key] = entry
    return entry


def _schedule(instance) -> None:
    bucket = pending_bucket()
    key = _key(instance)
    entry = bucket[key]
    if entry["scheduled"]:
        return
    entry["scheduled"] = True
    database = entry["database"]
    transaction.on_commit(lambda key=key: _flush(key), using=database)


def on_pre_save(sender, instance, raw: bool, **kwargs) -> None:
    if raw or current_actor() is None or pending_bucket() is None or not is_tracked(sender):
        return
    if not instance.pk:
        return
    existing = sender._meta.concrete_model.objects.using(database_of(instance)).filter(pk=instance.pk).first()
    if existing is None:
        return
    entry = _entry(instance)
    if entry["before_fields"] is None and not entry["created"]:
        entry["before_fields"] = snapshot_fields(existing)
        entry["before_children"] = snapshot_children(existing, child_relations(sender))


def on_post_save(sender, instance, created: bool, raw: bool, **kwargs) -> None:
    if raw or current_actor() is None or pending_bucket() is None or not is_tracked(sender):
        return
    entry = _entry(instance)
    if created:
        entry["created"] = True
    entry["database"] = database_of(instance)
    entry["pk"] = instance.pk
    _schedule(instance)


def on_pre_delete(sender, instance, **kwargs) -> None:
    if current_actor() is None or pending_bucket() is None or not is_tracked(sender):
        return
    entry = _entry(instance)
    entry["deleted"] = {
        "fields": snapshot_fields(instance),
        "children": snapshot_children(instance, child_relations(sender)),
        "label": object_label(instance),
    }
    entry["database"] = database_of(instance)
    entry["pk"] = instance.pk
    _schedule(instance)


def _flush(key: tuple[str, str, str, str]) -> None:
    bucket = pending_bucket()
    if bucket is None:
        return
    entry = bucket.pop(key, None)
    if entry is None:
        return
    if entry["deleted"] is not None:
        deleted = entry["deleted"]
        changes = field_changes(deleted["fields"], {}, AuditEvent.ACTION_DELETED)
        changes.update(child_changes(deleted["children"], {}, AuditEvent.ACTION_DELETED))
        write_event(
            entry["actor_id"],
            AuditEvent.ACTION_DELETED,
            entry["app_label"],
            entry["model"],
            str(entry["pk"]),
            deleted["label"],
            entry["database"],
            AuditEvent.SOURCE_USER,
            changes,
            None,
        )
        return
    model = apps.get_model(entry["app_label"], entry["model"])
    instance = model.objects.using(entry["database"]).filter(pk=entry["pk"]).first()
    if instance is None:
        return
    after_fields = snapshot_fields(instance)
    after_children = snapshot_children(instance, child_relations(type(instance)))
    if entry["created"]:
        action = AuditEvent.ACTION_CREATED
        changes = field_changes(None, after_fields, action)
        changes.update(child_changes({}, after_children, action))
    else:
        action = AuditEvent.ACTION_UPDATED
        changes = field_changes(entry["before_fields"], after_fields, action)
        changes.update(child_changes(entry["before_children"], after_children, action))
        if not changes:
            return
    write_event(
        entry["actor_id"],
        action,
        entry["app_label"],
        entry["model"],
        str(instance.pk),
        object_label(instance),
        entry["database"],
        AuditEvent.SOURCE_USER,
        changes,
        None,
    )
