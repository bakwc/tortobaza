from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User

from crm.models import CrmOrder, CrmOrderEvent

TRACKED_FIELDS = (
    "date",
    "time_start",
    "time_end",
    "when_ready",
    "contact",
    "nickname",
    "delivery_address",
    "fulfillment_type",
    "status",
    "taken_by_id",
    "created_by_id",
    "delivered_by_id",
    "weight",
    "filling",
    "description",
    "internal_description",
    "cake_price",
    "prepayment",
    "is_paid",
    "payment_type",
    "website_order_id",
    "flowwow_order_id",
    "deleted",
)

USER_ID_FIELDS = ("taken_by_id", "created_by_id", "delivered_by_id")


def _jsonable(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    return value


def snapshot_crm_order(order: CrmOrder) -> dict:
    data = {name: _jsonable(getattr(order, name)) for name in TRACKED_FIELDS}
    images = order.images.order_by("position", "id")
    data["images"] = [image.image.name for image in images]
    return data


def record_crm_order_event(
    order: CrmOrder,
    action: str,
    source: str,
    actor: User | None,
    before: dict | None,
) -> CrmOrderEvent | None:
    after = snapshot_crm_order(order)
    if action == CrmOrderEvent.ACTION_CREATED:
        changes = {key: {"old": None, "new": value} for key, value in after.items()}
    else:
        changes = {}
        for key, value in after.items():
            old = before[key]
            if old != value:
                changes[key] = {"old": old, "new": value}
        if not changes:
            return None
    return CrmOrderEvent.objects.create(
        order=order,
        action=action,
        source=source,
        actor=actor,
        changes=changes,
    )


def backfill_existing_crm_order_events(apps, schema_editor) -> None:
    Order = apps.get_model("crm", "CrmOrder")
    Event = apps.get_model("crm", "CrmOrderEvent")
    events = []
    for order in Order.objects.prefetch_related("images").order_by("id"):
        if order.created_by_id:
            source = CrmOrderEvent.SOURCE_CRM
            actor_id = order.created_by_id
        elif order.website_order_id:
            source = CrmOrderEvent.SOURCE_WEBSITE
            actor_id = None
        elif order.flowwow_order_id:
            source = CrmOrderEvent.SOURCE_FLOWWOW
            actor_id = None
        else:
            source = CrmOrderEvent.SOURCE_ADMIN
            actor_id = None
        after = snapshot_crm_order(order)
        changes = {key: {"old": None, "new": value} for key, value in after.items()}
        events.append(
            Event(
                order_id=order.pk,
                created_at=order.created_at,
                action=CrmOrderEvent.ACTION_CREATED,
                source=source,
                actor_id=actor_id,
                changes=changes,
            )
        )
    Event.objects.bulk_create(events)
