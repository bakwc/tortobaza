from datetime import date

from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q, TextField
from django.db.models.functions import Cast
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile
from accounts.permissions import (
    SectionPermission,
    can_see_order_contacts,
    redact_order_field_changes,
)
from audit.models import AuditEvent
from crm.models import CrmOrder

PAGE_SIZE = 50


def _hides_order_contacts(user, fulfillment_type: str | None) -> bool:
    if fulfillment_type is None:
        return not (
            can_see_order_contacts(user, "delivery") and can_see_order_contacts(user, "pickup")
        )
    return not can_see_order_contacts(user, fulfillment_type)


def _audit_order_row(event: AuditEvent, user, orders_by_id: dict[int, CrmOrder]) -> tuple[dict, str]:
    if event.app_label != "crm" or event.model != "crmorder":
        return event.changes, event.object_label
    order = None
    if event.object_id.isdigit():
        order = orders_by_id.get(int(event.object_id))
    fulfillment_type = None if order is None else order.fulfillment_type
    changes = redact_order_field_changes(user, fulfillment_type, event.changes)
    label = event.object_label
    if _hides_order_contacts(user, fulfillment_type):
        if order is None:
            label = f"#{event.object_id}"
        else:
            label = f"{order.date} #{order.id}"
    return changes, label


def _actor_names(actor_ids: list[int]) -> dict[int, str]:
    profiles = {
        profile.user_id: profile
        for profile in UserProfile.objects.filter(user_id__in=actor_ids)
    }
    names = {}
    for user in User.objects.filter(pk__in=actor_ids):
        profile = profiles.get(user.pk)
        if profile is None:
            names[user.pk] = user.username
            continue
        telegram_nick = profile.telegram_username.lstrip("@") if profile.telegram_username else ""
        if profile.internal_name:
            names[user.pk] = profile.internal_name
        elif telegram_nick:
            names[user.pk] = telegram_nick
        else:
            names[user.pk] = user.username
    return names


class AuditEventsView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("history")]

    def get(self, request):
        queryset = AuditEvent.objects.select_related("actor").all()
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        app_label = request.query_params.get("app")
        model_name = request.query_params.get("model")
        object_id = request.query_params.get("object_id")
        query = request.query_params.get("q")
        actor = request.query_params.get("actor")
        if start:
            queryset = queryset.filter(created_at__date__gte=date.fromisoformat(start))
        if end:
            queryset = queryset.filter(created_at__date__lte=date.fromisoformat(end))
        if app_label:
            queryset = queryset.filter(app_label=app_label)
        if model_name:
            queryset = queryset.filter(model=model_name)
        if object_id:
            queryset = queryset.filter(object_id=object_id)
        if actor:
            queryset = queryset.filter(actor_id=int(actor))
        if query:
            queryset = queryset.annotate(changes_text=Cast("changes", TextField())).filter(
                Q(object_label__icontains=query)
                | Q(actor__username__icontains=query)
                | Q(actor__first_name__icontains=query)
                | Q(actor__last_name__icontains=query)
                | Q(actor__profile__internal_name__icontains=query)
                | Q(actor__profile__telegram_username__icontains=query)
                | Q(changes_text__icontains=query)
            )
        page_param = request.query_params.get("page")
        page_number = 1 if page_param is None else int(page_param)
        page_size = queryset.count() or 1 if object_id else PAGE_SIZE
        page = Paginator(queryset, page_size).page(page_number)
        actor_ids = [event.actor_id for event in page.object_list if event.actor_id is not None]
        names = _actor_names(actor_ids)
        order_ids = [
            int(event.object_id)
            for event in page.object_list
            if event.app_label == "crm" and event.model == "crmorder" and event.object_id.isdigit()
        ]
        orders_by_id = {
            order.id: order for order in CrmOrder.objects.filter(id__in=order_ids)
        }
        results = []
        for event in page.object_list:
            changes, label = _audit_order_row(event, request.user, orders_by_id)
            results.append(
                {
                    "id": event.pk,
                    "created_at": event.created_at.isoformat(),
                    "actor_id": event.actor_id,
                    "actor_name": names.get(event.actor_id) if event.actor_id is not None else None,
                    "action": event.action,
                    "app_label": event.app_label,
                    "model": event.model,
                    "object_id": event.object_id,
                    "object_label": label,
                    "database": event.database,
                    "source": event.source,
                    "changes": changes,
                }
            )
        return Response(
            {
                "page": page.number,
                "pages": page.paginator.num_pages,
                "results": results,
            }
        )


class AuditActorsView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("history")]

    def get(self, request):
        actor_ids = list(
            AuditEvent.objects.exclude(actor_id=None).values_list("actor_id", flat=True).distinct()
        )
        names = _actor_names(actor_ids)
        actors = [
            {"id": actor_id, "name": names[actor_id]}
            for actor_id in actor_ids
            if actor_id in names
        ]
        actors.sort(key=lambda row: row["name"].lower())
        return Response(actors)
