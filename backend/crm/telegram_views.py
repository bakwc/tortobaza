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
from crm.models import SocialKeyword, SocialMessage, SocialNetwork, SocialSource, normalize_telegram_username
from crm.serializers import (
    SocialKeywordSerializer,
    SocialMessageIngestSerializer,
    SocialMessageSerializer,
    SocialNetworkSerializer,
    SocialSourceSerializer,
)
from crm.telegram_channels import _keyword_match, refresh_keyword_matches
from crm.telegram_leads import classify_leads, notify_recent_leads

PAGE_SIZE = 15


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
        qs = SocialMessage.objects.select_related("channel", "channel__network").order_by(
            "-sent_at",
            "-external_id",
        )
        if network_param:
            qs = qs.filter(channel__network__slug=network_param)
        if channel_param is not None:
            qs = qs.filter(channel_id=int(channel_param))
        if kind == "keyword":
            qs = qs.filter(keyword_match=True)
        elif kind == "all":
            pass
        else:
            qs = qs.filter(potential_lead=True)
        stripped = q.strip()
        if stripped:
            needle = stripped.casefold()
            rows = [row for row in qs if needle in row.text.casefold()]
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
        keywords = [row.casefold() for row in SocialKeyword.objects.values_list("word", flat=True)]
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
                SocialMessage.objects.create(
                    channel=source,
                    external_id=external_id,
                    sent_at=item["sent_at"],
                    text=item["text"],
                    sender_id=sender_id,
                    sender_username=item["sender_username"],
                    url=item["url"],
                    location=item["location"],
                    topic=item["topic"],
                    keyword_match=_keyword_match(item["text"], keywords),
                )
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
        classify_leads(slug)
        notify_recent_leads(slug)
        return Response(status=status.HTTP_204_NO_CONTENT)
