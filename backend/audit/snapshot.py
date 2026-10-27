import json
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from django.db import models

from audit.context import database_of


def jsonable(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _sensitive(name: str) -> bool:
    lowered = name.lower()
    return name in {"password", "last_login"} or "token" in lowered or "secret" in lowered


def snapshot_fields(instance: models.Model) -> dict:
    data = {}
    for field in instance._meta.concrete_fields:
        if field.primary_key:
            continue
        if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
            continue
        if _sensitive(field.name):
            continue
        if isinstance(field, models.FileField):
            file_value = getattr(instance, field.name)
            data[field.attname] = file_value.name if file_value else ""
            continue
        data[field.attname] = jsonable(getattr(instance, field.attname))
    return data


def canonical_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False))


def snapshot_children(instance: models.Model, relations: tuple[str, ...]) -> dict[str, list[dict]]:
    data = {}
    for name in relations:
        manager = getattr(instance, name)
        data[name] = canonical_rows([snapshot_fields(child) for child in manager.all()])
    return data


def object_label(instance: models.Model) -> str:
    return str(instance)[:255]


def field_changes(before: dict | None, after: dict, action: str) -> dict:
    changes = {}
    if action == "created":
        for key, value in after.items():
            changes[key] = {"old": None, "new": value}
        return changes
    if action == "deleted":
        for key, value in before.items():
            changes[key] = {"old": value, "new": None}
        return changes
    for key, value in after.items():
        old = before[key]
        if old != value:
            changes[key] = {"old": old, "new": value}
    return changes


def child_changes(before: dict[str, list], after: dict[str, list], action: str) -> dict:
    changes = {}
    if action == "created":
        for name, new in after.items():
            if new:
                changes[name] = {"old": [], "new": new}
        return changes
    if action == "deleted":
        for name, old in before.items():
            if old:
                changes[name] = {"old": old, "new": None}
        return changes
    for name in before:
        old = before[name]
        new = after[name]
        if old != new:
            changes[name] = {"old": old, "new": new}
    return changes


def instance_database(instance: models.Model) -> str:
    return database_of(instance)
