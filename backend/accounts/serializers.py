from decimal import Decimal

from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models import Q
from rest_framework import serializers

from accounts.models import UserProfile
from accounts.permissions import admin_model_permissions, section_codenames, user_section_codes

PROFILE_FIELDS = (
    "hourly_rate",
    "monthly_rate",
    "can_login",
    "telegram_username",
    "internal_name",
    "gender",
    "is_active_courier",
    "pushover_user",
    "position",
    "in_schedule",
)


class UserSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    internal_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "is_staff", "permissions", "internal_name"]

    def get_permissions(self, user: User) -> list[str]:
        return user_section_codes(user)

    def get_internal_name(self, user: User) -> str:
        internal_name = UserProfile.objects.filter(user_id=user.pk).values_list("internal_name", flat=True).first()
        if internal_name is None:
            return ""
        return internal_name


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
    is_active_courier = serializers.BooleanField()
    groups = serializers.ListField(child=serializers.IntegerField(), allow_empty=True)
    pushover_user = serializers.CharField(max_length=30, allow_blank=True)
    position = serializers.CharField(max_length=64, allow_blank=True)
    in_schedule = serializers.BooleanField()

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": ["This field is required."]})
        taken = User.objects.filter(username=attrs["username"])
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError({"username": ["A user with that username already exists."]})
        return attrs

    def validate_groups(self, value: list[int]) -> list[int]:
        ids = list(dict.fromkeys(value))
        found = set(Group.objects.filter(pk__in=ids).values_list("pk", flat=True))
        if len(found) != len(ids):
            raise serializers.ValidationError("Unknown group.")
        return ids

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
        user.groups.set(validated_data["groups"])
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
        instance.groups.set(validated_data["groups"])
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
            is_active_courier = False
            pushover_user = ""
            position = ""
            in_schedule = False
        else:
            hourly_rate = profile.hourly_rate
            monthly_rate = profile.monthly_rate
            can_login = profile.can_login
            telegram_username = profile.telegram_username
            internal_name = profile.internal_name
            gender = profile.gender
            is_active_courier = profile.is_active_courier
            pushover_user = profile.pushover_user
            position = profile.position
            in_schedule = profile.in_schedule
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
            "is_active_courier": is_active_courier,
            "groups": list(instance.groups.values_list("id", flat=True)),
            "pushover_user": pushover_user,
            "position": position,
            "in_schedule": in_schedule,
        }

    def _apply_profile(self, profile, validated_data):
        for field in PROFILE_FIELDS:
            setattr(profile, field, validated_data[field])


class AccessGroupSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=150)
    permissions = serializers.ListField(child=serializers.CharField(), allow_empty=True)

    def validate_name(self, value: str) -> str:
        taken = Group.objects.filter(name=value)
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError("A group with that name already exists.")
        return value

    def validate_permissions(self, value: list[str]) -> list[str]:
        codes = list(dict.fromkeys(value))
        known = section_codenames()
        unknown = [code for code in codes if code not in known]
        if unknown:
            raise serializers.ValidationError("Unknown permission.")
        return codes

    def create(self, validated_data):
        group = Group.objects.create(name=validated_data["name"])
        self._apply_permissions(group, validated_data["permissions"])
        return group

    def update(self, instance, validated_data):
        instance.name = validated_data["name"]
        instance.save(update_fields=["name"])
        self._apply_permissions(instance, validated_data["permissions"])
        return instance

    def to_representation(self, instance):
        known = section_codenames()
        codes = [
            perm.codename
            for perm in instance.permissions.all()
            if perm.content_type.app_label == "accounts" and perm.codename in known
        ]
        return {"id": instance.id, "name": instance.name, "permissions": sorted(codes)}

    def _apply_permissions(self, group, codes: list[str]) -> None:
        perms = list(
            Permission.objects.filter(
                content_type__app_label="accounts",
                content_type__model="sectionaccess",
                codename__in=codes,
            )
        )
        if len(perms) != len(codes):
            raise RuntimeError("Section permission rows are missing.")
        catalog_perms = admin_model_permissions(codes)
        managed = list(
            group.permissions.filter(
                Q(content_type__app_label="accounts", content_type__model="sectionaccess")
                | Q(content_type__app_label="catalog")
            )
        )
        if managed:
            group.permissions.remove(*managed)
        wanted = perms + catalog_perms
        if wanted:
            group.permissions.add(*wanted)
