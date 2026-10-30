from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import EmployeeSerializer, LoginSerializer, UserSerializer
from crm.views import IsFinanceAdmin


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
    return User.objects.select_related("profile").order_by("username")


class EmployeeListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsFinanceAdmin]

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
    permission_classes = [IsFinanceAdmin]

    @transaction.atomic
    def put(self, request, pk: int):
        user = get_object_or_404(employee_queryset(), pk=pk)
        serializer = EmployeeSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user = employee_queryset().get(pk=user.pk)
        return Response(EmployeeSerializer(user).data)
