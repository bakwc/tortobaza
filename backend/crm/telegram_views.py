from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import SectionPermission
from crm.models import TelegramChannel, TelegramChannelMessage, TelegramKeyword
from crm.serializers import (
    TelegramChannelMessageSerializer,
    TelegramChannelSerializer,
    TelegramKeywordSerializer,
)
from crm.telegram_channels import refresh_keyword_matches

PAGE_SIZE = 15


class TelegramMessageListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]

    def get(self, request):
        kind = request.query_params.get("kind", "lead")
        q = request.query_params.get("q", "")
        channel_param = request.query_params.get("channel")
        page_param = request.query_params.get("page")
        page_number = 1 if page_param is None else int(page_param)
        qs = TelegramChannelMessage.objects.select_related("channel").order_by("-sent_at", "-message_id")
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
                "results": TelegramChannelMessageSerializer(page.object_list, many=True).data,
            }
        )


class TelegramChannelListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]
    serializer_class = TelegramChannelSerializer

    def get(self, request):
        qs = TelegramChannel.objects.all()
        return Response(self.serializer_class(qs, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data, status=status.HTTP_201_CREATED)


class TelegramChannelDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]
    serializer_class = TelegramChannelSerializer

    def get(self, request, pk: int):
        instance = get_object_or_404(TelegramChannel.objects.all(), pk=pk)
        return Response(self.serializer_class(instance).data)

    @transaction.atomic
    def put(self, request, pk: int):
        instance = get_object_or_404(TelegramChannel.objects.all(), pk=pk)
        serializer = self.serializer_class(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data)

    @transaction.atomic
    def delete(self, request, pk: int):
        instance = get_object_or_404(TelegramChannel.objects.all(), pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TelegramKeywordListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]
    serializer_class = TelegramKeywordSerializer

    def get(self, request):
        qs = TelegramKeyword.objects.all()
        return Response(self.serializer_class(qs, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        refresh_keyword_matches()
        return Response(self.serializer_class(instance).data, status=status.HTTP_201_CREATED)


class TelegramKeywordDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]
    serializer_class = TelegramKeywordSerializer

    def get(self, request, pk: int):
        instance = get_object_or_404(TelegramKeyword.objects.all(), pk=pk)
        return Response(self.serializer_class(instance).data)

    @transaction.atomic
    def put(self, request, pk: int):
        instance = get_object_or_404(TelegramKeyword.objects.all(), pk=pk)
        serializer = self.serializer_class(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        refresh_keyword_matches()
        return Response(self.serializer_class(instance).data)

    @transaction.atomic
    def delete(self, request, pk: int):
        instance = get_object_or_404(TelegramKeyword.objects.all(), pk=pk)
        instance.delete()
        refresh_keyword_matches()
        return Response(status=status.HTTP_204_NO_CONTENT)
