from decimal import Decimal

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers

from accounts.models import UserProfile

PROFILE_FIELDS = (
    "hourly_rate",
    "monthly_rate",
    "can_login",
    "telegram_username",
    "internal_name",
    "gender",
    "is_finance_admin",
    "is_active_courier",
    "pushover_user",
)


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


class EmployeeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(max_length=150, validators=[UnicodeUsernameValidator()])
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150, allow_blank=True)
    last_name = serializers.CharField(max_length=150, allow_blank=True)
    email = serializers.EmailField(max_length=254, allow_blank=True)
    is_active = serializers.BooleanField()
    is_staff = serializers.BooleanField()
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2)
    monthly_rate = serializers.DecimalField(max_digits=10, decimal_places=2)
    can_login = serializers.BooleanField()
    telegram_username = serializers.CharField(max_length=32, allow_blank=True)
    internal_name = serializers.CharField(max_length=64, allow_blank=True)
    gender = serializers.ChoiceField(choices=UserProfile.GENDER_CHOICES)
    is_finance_admin = serializers.BooleanField()
    is_active_courier = serializers.BooleanField()
    pushover_user = serializers.CharField(max_length=30, allow_blank=True)

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": ["This field is required."]})
        taken = User.objects.filter(username=attrs["username"])
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError({"username": ["A user with that username already exists."]})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            is_active=validated_data["is_active"],
            is_staff=validated_data["is_staff"],
        )
        profile = UserProfile(user=user)
        self._apply_profile(profile, validated_data)
        profile.save()
        return user

    def update(self, instance, validated_data):
        instance.username = validated_data["username"]
        instance.first_name = validated_data["first_name"]
        instance.last_name = validated_data["last_name"]
        instance.email = validated_data["email"]
        instance.is_active = validated_data["is_active"]
        instance.is_staff = validated_data["is_staff"]
        password = validated_data.get("password") or ""
        if password:
            instance.set_password(password)
        instance.save()
        profile = UserProfile.objects.filter(user=instance).first()
        if profile is None:
            profile = UserProfile(user=instance)
        self._apply_profile(profile, validated_data)
        profile.save()
        return instance

    def to_representation(self, instance):
        profile = getattr(instance, "profile", None)
        if profile is None:
            hourly_rate = Decimal("0.00")
            monthly_rate = Decimal("0.00")
            can_login = True
            telegram_username = ""
            internal_name = ""
            gender = UserProfile.GENDER_FEMALE
            is_finance_admin = False
            is_active_courier = False
            pushover_user = ""
        else:
            hourly_rate = profile.hourly_rate
            monthly_rate = profile.monthly_rate
            can_login = profile.can_login
            telegram_username = profile.telegram_username
            internal_name = profile.internal_name
            gender = profile.gender
            is_finance_admin = profile.is_finance_admin
            is_active_courier = profile.is_active_courier
            pushover_user = profile.pushover_user
        return {
            "id": instance.id,
            "username": instance.username,
            "first_name": instance.first_name,
            "last_name": instance.last_name,
            "email": instance.email,
            "is_active": instance.is_active,
            "is_staff": instance.is_staff,
            "hourly_rate": self.fields["hourly_rate"].to_representation(hourly_rate),
            "monthly_rate": self.fields["monthly_rate"].to_representation(monthly_rate),
            "can_login": can_login,
            "telegram_username": telegram_username,
            "internal_name": internal_name,
            "gender": gender,
            "is_finance_admin": is_finance_admin,
            "is_active_courier": is_active_courier,
            "pushover_user": pushover_user,
        }

    def _apply_profile(self, profile, validated_data):
        for field in PROFILE_FIELDS:
            setattr(profile, field, validated_data[field])
