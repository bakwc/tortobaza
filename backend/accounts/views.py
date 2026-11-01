from django.contrib.auth import login, logout
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import SectionPermission, permission_rows
from accounts.serializers import AccessGroupSerializer, EmployeeSerializer, LoginSerializer, UserSerializer


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "CSRF cookie set."})


class LoginView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


def employee_queryset():
    return User.objects.select_related("profile").prefetch_related("groups").order_by("username")


def group_queryset():
    return Group.objects.prefetch_related("permissions__content_type").order_by("name", "id")


class EmployeeListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("employees")]

    def get(self, request):
        return Response(EmployeeSerializer(employee_queryset(), many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = EmployeeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user = employee_queryset().get(pk=user.pk)
        return Response(EmployeeSerializer(user).data, status=status.HTTP_201_CREATED)


class EmployeeDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("employees")]

    @transaction.atomic
    def put(self, request, pk: int):
        user = get_object_or_404(employee_queryset(), pk=pk)
        serializer = EmployeeSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user = employee_queryset().get(pk=user.pk)
        return Response(EmployeeSerializer(user).data)


class PermissionListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("employees")]

    def get(self, request):
        return Response(permission_rows())


class GroupListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("employees")]

    def get(self, request):
        return Response(AccessGroupSerializer(group_queryset(), many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = AccessGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        group = group_queryset().get(pk=group.pk)
        return Response(AccessGroupSerializer(group).data, status=status.HTTP_201_CREATED)


class GroupDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("employees")]

    @transaction.atomic
    def put(self, request, pk: int):
        group = get_object_or_404(group_queryset(), pk=pk)
        serializer = AccessGroupSerializer(group, data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        group = group_queryset().get(pk=group.pk)
        return Response(AccessGroupSerializer(group).data)

    @transaction.atomic
    def delete(self, request, pk: int):
        group = get_object_or_404(Group, pk=pk)
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
