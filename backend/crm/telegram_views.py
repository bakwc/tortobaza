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
        channel_param = request.query_params.get("channel")
        page_param = request.query_params.get("page")
        page_number = 1 if page_param is None else int(page_param)
        qs = SocialMessage.objects.select_related("channel", "channel__network").order_by(
            "-sent_at",
            "-external_id",
        )
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
        username = data["source_key"]
        if network.slug == "telegram":
            username = normalize_telegram_username(username)
        source, _created = SocialSource.objects.get_or_create(
            network=network,
            username=username,
            defaults={
                "title": data["source_title"],
                "enabled": True,
            },
        )
        if source.title != data["source_title"]:
            source.title = data["source_title"]
            source.save(update_fields=["title"])
        sender_id = data["sender_id"]
        if sender_id == "":
            sender_id = None
        message = SocialMessage.objects.filter(channel=source, external_id=data["external_id"]).first()
        if message is None:
            keywords = [row.casefold() for row in SocialKeyword.objects.values_list("word", flat=True)]
            message = SocialMessage.objects.create(
                channel=source,
                external_id=data["external_id"],
                sent_at=data["sent_at"],
                text=data["text"],
                sender_id=sender_id,
                sender_username=data["sender_username"],
                url=data["url"],
                keyword_match=_keyword_match(data["text"], keywords),
            )
            created = True
        else:
            update_fields = []
            if message.sent_at != data["sent_at"]:
                message.sent_at = data["sent_at"]
                update_fields.append("sent_at")
            if message.text != data["text"]:
                keywords = [row.casefold() for row in SocialKeyword.objects.values_list("word", flat=True)]
                message.text = data["text"]
                message.keyword_match = _keyword_match(data["text"], keywords)
                update_fields.extend(["text", "keyword_match"])
            if message.sender_id != sender_id:
                message.sender_id = sender_id
                update_fields.append("sender_id")
            if message.sender_username != data["sender_username"]:
                message.sender_username = data["sender_username"]
                update_fields.append("sender_username")
            if message.url != data["url"]:
                message.url = data["url"]
                update_fields.append("url")
            if update_fields:
                message.save(update_fields=update_fields)
            created = False
        return Response(
            {"id": message.id, "keyword_match": message.keyword_match},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
