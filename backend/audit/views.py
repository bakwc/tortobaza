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
from audit.models import AuditEvent
from crm.views import IsFinanceAdmin

PAGE_SIZE = 50


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
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def get(self, request):
        queryset = AuditEvent.objects.select_related("actor").all()
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        app_label = request.query_params.get("app")
        model_name = request.query_params.get("model")
        object_id = request.query_params.get("object_id")
        query = request.query_params.get("q")
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
        return Response(
            {
                "page": page.number,
                "pages": page.paginator.num_pages,
                "results": [
                    {
                        "id": event.pk,
                        "created_at": event.created_at.isoformat(),
                        "actor_id": event.actor_id,
                        "actor_name": names.get(event.actor_id) if event.actor_id is not None else None,
                        "action": event.action,
                        "app_label": event.app_label,
                        "model": event.model,
                        "object_id": event.object_id,
                        "object_label": event.object_label,
                        "database": event.database,
                        "source": event.source,
                        "changes": event.changes,
                    }
                    for event in page.object_list
                ],
            }
        )
