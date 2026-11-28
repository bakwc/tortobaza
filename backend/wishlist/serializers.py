from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers

from accounts.models import chef_identity
from wishlist.models import Idea, Task, WishlistItem


class WishlistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WishlistItem
        fields = ["id", "title", "purpose", "priority", "cost"]


class DurationSecondsField(serializers.Field):
    default_error_messages = {
        "invalid": "Duration must be a non-negative integer number of seconds.",
    }

    def to_representation(self, value):
        if value is None:
            return None
        return int(value.total_seconds())

    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, int) or data < 0:
            self.fail("invalid")
        return timedelta(seconds=data)


class IdeaSerializer(serializers.ModelSerializer):
    duration_seconds = DurationSecondsField(allow_null=True, source="duration")

    class Meta:
        model = Idea
        fields = [
            "id",
            "priority",
            "problem",
            "description",
            "cost",
            "duration_seconds",
            "status",
        ]


class TaskSerializer(serializers.ModelSerializer):
    assignee = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True))
    author_name = serializers.SerializerMethodField()
    assignee_name = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "assignee",
            "author",
            "author_name",
            "assignee_name",
            "created_at",
            "completed_at",
        ]
        read_only_fields = ["author", "author_name", "assignee_name", "created_at", "completed_at"]

    def get_author_name(self, obj: Task) -> str:
        return chef_identity(obj.author)[0]

    def get_assignee_name(self, obj: Task) -> str:
        return chef_identity(obj.assignee)[0]

    def create(self, validated_data):
        if validated_data["status"] == Task.STATUS_DONE:
            validated_data["completed_at"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        status = validated_data.get("status", instance.status)
        if status == Task.STATUS_DONE and instance.status != Task.STATUS_DONE:
            validated_data["completed_at"] = timezone.now()
        elif status != Task.STATUS_DONE:
            validated_data["completed_at"] = None
        return super().update(instance, validated_data)
