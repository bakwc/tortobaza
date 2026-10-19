from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import UserProfile


class UserSerializer(serializers.ModelSerializer):
    is_finance_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "is_staff", "is_finance_admin"]

    def get_is_finance_admin(self, user: User) -> bool:
        profile = UserProfile.objects.filter(user=user).first()
        if profile is None:
            return False
        return profile.is_finance_admin


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        user = authenticate(
            request=self.context["request"],
            username=attrs["username"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid username or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")
        profile = UserProfile.objects.filter(user=user).first()
        if profile is not None and not profile.can_login:
            raise serializers.ValidationError("Invalid username or password.")
        attrs["user"] = user
        return attrs
