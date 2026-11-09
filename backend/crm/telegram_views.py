import hmac

from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import SectionPermission
from crm.models import (
    LeadVertical,
    SocialKeyword,
    SocialLead,
    SocialMessage,
    SocialNetwork,
    SocialSearchQuery,
    SocialSource,
    append_processing_event,
    normalize_telegram_username,
)
from crm.serializers import (
    LeadVerticalSerializer,
    SocialKeywordSerializer,
    SocialMessageContextSerializer,
    SocialMessageIngestSerializer,
    SocialMessageSerializer,
    SocialNetworkSerializer,
    SocialPotentialLeadSerializer,
    SocialSearchQueryPublicSerializer,
    SocialSearchQuerySerializer,
    SocialSourceSerializer,
)
from crm.telegram_channels import apply_keyword_matches, refresh_keyword_matches
from crm.telegram_leads import classify_leads, notify_recent_leads, verify_leads

PAGE_SIZE = 15


def _message_search_terms(q: str) -> tuple[str, list[str]]:
    positives: list[str] = []
    negatives: list[str] = []
    for token in q.split():
        if token.startswith("-") and len(token) > 1:
            negatives.append(token[1:].casefold())
        else:
            positives.append(token)
    return " ".join(positives).casefold(), negatives


def _ingest_authorized(request) -> bool:
    expected = settings.SOCIAL_INGEST_TOKEN
    if not expected:
        return False
    header = request.headers.get("Authorization")
    if header is None or not header.startswith("Bearer "):
        return False
    token = header.removeprefix("Bearer ")
    if len(token) != len(expected):
        return False
    return hmac.compare_digest(token, expected)


class SocialMessageListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]

    def get(self, request):
        kind = request.query_params.get("kind", "lead")
        q = request.query_params.get("q", "")
        network_param = request.query_params.get("network")
        channel_param = request.query_params.get("channel")
        page_param = request.query_params.get("page")
        page_number = 1 if page_param is None else int(page_param)
        vertical_param = request.query_params.get("vertical")
        qs = SocialMessage.objects.select_related("channel", "channel__network").prefetch_related(
            "leads",
            "leads__vertical",
        ).order_by(
            "-sent_at",
            "-external_id",
        )
        if network_param:
            qs = qs.filter(channel__network__slug=network_param)
        if channel_param is not None:
            qs = qs.filter(channel_id=int(channel_param))
        lead_filters: dict[str, object] = {}
        if vertical_param:
            lead_filters["vertical__slug"] = vertical_param
        if kind == "keyword":
            lead_filters["keyword_match"] = True
        elif kind == "potential":
            lead_filters["potential_lead"] = True
        elif kind == "all":
            pass
        else:
            lead_filters["lead"] = True
        if lead_filters:
            qs = qs.filter(id__in=SocialLead.objects.filter(**lead_filters).values("message_id"))
        stripped = q.strip()
        if stripped:
            needle, excluded = _message_search_terms(stripped)
            rows = []
            for row in qs:
                text = row.text.casefold()
                if needle and needle not in text:
                    continue
                if any(term in text for term in excluded):
                    continue
                rows.append(row)
            page = Paginator(rows, PAGE_SIZE).page(page_number)
        else:
            page = Paginator(qs, PAGE_SIZE).page(page_number)
        return Response(
            {
                "page": page.number,
                "pages": page.paginator.num_pages,
                "results": SocialMessageSerializer(page.object_list, many=True).data,
            }
        )


class SocialSourceListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]
    serializer_class = SocialSourceSerializer

    def get(self, request):
        qs = SocialSource.objects.select_related("network")
        return Response(self.serializer_class(qs, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data, status=status.HTTP_201_CREATED)


class SocialSourceDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]
    serializer_class = SocialSourceSerializer

    def get(self, request, pk: int):
        instance = get_object_or_404(SocialSource.objects.select_related("network"), pk=pk)
        return Response(self.serializer_class(instance).data)

    @transaction.atomic
    def put(self, request, pk: int):
        instance = get_object_or_404(SocialSource.objects.select_related("network"), pk=pk)
        serializer = self.serializer_class(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data)

    @transaction.atomic
    def delete(self, request, pk: int):
        instance = get_object_or_404(SocialSource.objects.all(), pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SocialKeywordListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]
    serializer_class = SocialKeywordSerializer

    def get(self, request):
        qs = SocialKeyword.objects.all()
        vertical = request.query_params.get("vertical")
        if vertical:
            qs = qs.filter(vertical_id=int(vertical))
        return Response(self.serializer_class(qs, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        refresh_keyword_matches()
        return Response(self.serializer_class(instance).data, status=status.HTTP_201_CREATED)


class SocialKeywordDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]
    serializer_class = SocialKeywordSerializer

    def get(self, request, pk: int):
        instance = get_object_or_404(SocialKeyword.objects.all(), pk=pk)
        return Response(self.serializer_class(instance).data)

    @transaction.atomic
    def put(self, request, pk: int):
        instance = get_object_or_404(SocialKeyword.objects.all(), pk=pk)
        serializer = self.serializer_class(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        refresh_keyword_matches()
        return Response(self.serializer_class(instance).data)

    @transaction.atomic
    def delete(self, request, pk: int):
        instance = get_object_or_404(SocialKeyword.objects.all(), pk=pk)
        instance.delete()
        refresh_keyword_matches()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_exempt, name="dispatch")
class SocialNetworkIngestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = SocialNetworkSerializer

    def get(self, request):
        if not _ingest_authorized(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = SocialNetwork.objects.all()
        return Response(self.serializer_class(qs, many=True).data)

    def post(self, request):
        if not _ingest_authorized(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class SocialMessageIngestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not _ingest_authorized(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = SocialMessageIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        network = SocialNetwork.objects.get(slug=data["network"])
        created_count = 0
        skipped_count = 0
        seen: set[str] = set()
        with transaction.atomic():
            for item in data["messages"]:
                external_id = item["external_id"]
                if (
                    external_id in seen
                    or SocialMessage.objects.filter(
                        channel__network=network,
                        external_id=external_id,
                    ).exists()
                ):
                    skipped_count += 1
                    continue
                seen.add(external_id)
                username = item["source_key"]
                if network.slug == "telegram":
                    username = normalize_telegram_username(username)
                source, _created = SocialSource.objects.get_or_create(
                    network=network,
                    username=username,
                    defaults={
                        "title": item["source_title"],
                        "enabled": True,
                    },
                )
                sender_id = item["sender_id"]
                if sender_id == "":
                    sender_id = None
                row = SocialMessage(
                    channel=source,
                    external_id=external_id,
                    sent_at=item["sent_at"],
                    text=item["text"],
                    sender_id=sender_id,
                    sender_username=item["sender_username"],
                    url=item["url"],
                    location=item["location"],
                    topic=item["topic"],
                )
                row.save()
                apply_keyword_matches(row)
                created_count += 1
        return Response({"created": created_count, "skipped": skipped_count})


@method_decorator(csrf_exempt, name="dispatch")
class SocialLeadsProcessView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, slug: str):
        if not _ingest_authorized(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        get_object_or_404(SocialNetwork, slug=slug)
        if slug == "telegram":
            return Response(status=status.HTTP_400_BAD_REQUEST)
        raw = request.query_params.get("potential", "false")
        if raw not in ("true", "false"):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        classify_leads(slug, raw == "true")
        notify_recent_leads(slug)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_exempt, name="dispatch")
class SocialPotentialLeadsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, slug: str):
        if not _ingest_authorized(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        network = get_object_or_404(SocialNetwork, slug=slug)
        if slug == "telegram":
            return Response(status=status.HTTP_400_BAD_REQUEST)
        message_ids = SocialLead.objects.filter(
            message__channel__network=network,
            potential_lead=True,
            lead__isnull=True,
            message__context__isnull=True,
        ).values("message_id")
        rows = SocialMessage.objects.filter(id__in=message_ids).order_by("id")
        return Response(SocialPotentialLeadSerializer(rows, many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class SocialMessageContextView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, pk: int):
        if not _ingest_authorized(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        message = get_object_or_404(SocialMessage, pk=pk)
        serializer = SocialMessageContextSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.validated_data["profile"]
        message.context = [
            {
                "username": item["username"],
                "text": item["text"],
                "sent_at": item["sent_at"].isoformat(),
                "url": item["url"],
            }
            for item in serializer.validated_data["context"]
        ]
        message.profile = {
            "title": profile["title"],
            "description": profile["description"],
            "posts": [
                {
                    "text": item["text"],
                    "sent_at": item["sent_at"].isoformat(),
                    "url": item["url"],
                }
                for item in profile["posts"]
            ],
        }
        append_processing_event(message, {"kind": "context"})
        message.save(update_fields=["context", "profile", "processing_history"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_exempt, name="dispatch")
class SocialLeadsVerifyView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, slug: str):
        if not _ingest_authorized(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        get_object_or_404(SocialNetwork, slug=slug)
        if slug == "telegram":
            return Response(status=status.HTTP_400_BAD_REQUEST)
        verify_leads(slug)
        notify_recent_leads(slug)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeadVerticalListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]
    serializer_class = LeadVerticalSerializer

    def get(self, request):
        qs = LeadVertical.objects.all()
        return Response(self.serializer_class(qs, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data, status=status.HTTP_201_CREATED)


class LeadVerticalDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]
    serializer_class = LeadVerticalSerializer

    def get(self, request, pk: int):
        instance = get_object_or_404(LeadVertical.objects.all(), pk=pk)
        return Response(self.serializer_class(instance).data)

    @transaction.atomic
    def put(self, request, pk: int):
        instance = get_object_or_404(LeadVertical.objects.all(), pk=pk)
        serializer = self.serializer_class(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data)

    @transaction.atomic
    def delete(self, request, pk: int):
        instance = get_object_or_404(LeadVertical.objects.all(), pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SocialSearchQueryListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]
    serializer_class = SocialSearchQuerySerializer

    def get(self, request):
        qs = SocialSearchQuery.objects.all()
        return Response(self.serializer_class(qs, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data, status=status.HTTP_201_CREATED)


class SocialSearchQueryDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]
    serializer_class = SocialSearchQuerySerializer

    def get(self, request, pk: int):
        instance = get_object_or_404(SocialSearchQuery.objects.all(), pk=pk)
        return Response(self.serializer_class(instance).data)

    @transaction.atomic
    def put(self, request, pk: int):
        instance = get_object_or_404(SocialSearchQuery.objects.all(), pk=pk)
        serializer = self.serializer_class(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data)

    @transaction.atomic
    def delete(self, request, pk: int):
        instance = get_object_or_404(SocialSearchQuery.objects.all(), pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_exempt, name="dispatch")
class SocialSearchQueryIngestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = SocialSearchQueryPublicSerializer

    def get(self, request):
        if not _ingest_authorized(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = SocialSearchQuery.objects.filter(enabled=True)
        return Response(self.serializer_class(qs, many=True).data)
