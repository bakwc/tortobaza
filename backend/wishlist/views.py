from datetime import timedelta

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import chef_identity
from accounts.permissions import SectionPermission
from wishlist.models import Idea, Task, WishlistItem
from wishlist.serializers import IdeaSerializer, TaskSerializer, WishlistItemSerializer


class WishlistListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("wishlist")]
    serializer_class = WishlistItemSerializer

    def get(self, request):
        return Response(self.serializer_class(WishlistItem.objects.all(), many=True).data)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data, status=status.HTTP_201_CREATED)


class WishlistDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("wishlist")]
    serializer_class = WishlistItemSerializer

    def get(self, request, pk: int):
        instance = get_object_or_404(WishlistItem.objects.all(), pk=pk)
        return Response(self.serializer_class(instance).data)

    def put(self, request, pk: int):
        instance = get_object_or_404(WishlistItem.objects.all(), pk=pk)
        serializer = self.serializer_class(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data)

    def delete(self, request, pk: int):
        instance = get_object_or_404(WishlistItem.objects.all(), pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IdeaListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("wishlist")]
    serializer_class = IdeaSerializer

    def get(self, request):
        return Response(self.serializer_class(Idea.objects.ordered(), many=True).data)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data, status=status.HTTP_201_CREATED)


class IdeaDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("wishlist")]
    serializer_class = IdeaSerializer

    def get(self, request, pk: int):
        instance = get_object_or_404(Idea.objects.all(), pk=pk)
        return Response(self.serializer_class(instance).data)

    def put(self, request, pk: int):
        instance = get_object_or_404(Idea.objects.all(), pk=pk)
        serializer = self.serializer_class(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data)

    def delete(self, request, pk: int):
        instance = get_object_or_404(Idea.objects.all(), pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def task_queryset():
    return Task.objects.select_related("author__profile", "assignee__profile")


class TaskListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("wishlist")]
    serializer_class = TaskSerializer

    def get(self, request):
        hide_old_done = serializers.BooleanField().run_validation(request.query_params.get("hide_old_done"))
        queryset = task_queryset()
        if hide_old_done:
            cutoff = timezone.now() - timedelta(days=30)
            queryset = queryset.exclude(status=Task.STATUS_DONE, completed_at__lt=cutoff)
        return Response(self.serializer_class(queryset, many=True).data)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(author=request.user)
        return Response(self.serializer_class(instance).data, status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("wishlist")]
    serializer_class = TaskSerializer

    def get(self, request, pk: int):
        instance = get_object_or_404(task_queryset(), pk=pk)
        return Response(self.serializer_class(instance).data)

    def put(self, request, pk: int):
        instance = get_object_or_404(task_queryset(), pk=pk)
        serializer = self.serializer_class(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data)

    def delete(self, request, pk: int):
        instance = get_object_or_404(task_queryset(), pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskAssigneeListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("wishlist")]

    def get(self, request):
        users = User.objects.filter(is_active=True).select_related("profile")
        rows = [{"id": user.id, "name": chef_identity(user)[0]} for user in users]
        rows.sort(key=lambda row: row["name"])
        return Response(rows)
