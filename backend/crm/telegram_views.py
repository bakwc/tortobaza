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


class TelegramMessageListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("leads")]

    def get(self, request):
        kind = request.query_params.get("kind", "lead")
        q = request.query_params.get("q", "")
        qs = TelegramChannelMessage.objects.select_related("channel").order_by("-sent_at", "-message_id")
        if kind == "keyword":
            qs = qs.filter(keyword_match=True)
        elif kind == "all":
            pass
        else:
            qs = qs.filter(potential_lead=True)
        rows = list(qs)
        stripped = q.strip()
        if stripped:
            needle = stripped.casefold()
            rows = [row for row in rows if needle in row.text.casefold()]
        return Response(TelegramChannelMessageSerializer(rows, many=True).data)


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
        return Response(self.serializer_class(instance).data)

    @transaction.atomic
    def delete(self, request, pk: int):
        instance = get_object_or_404(TelegramKeyword.objects.all(), pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
