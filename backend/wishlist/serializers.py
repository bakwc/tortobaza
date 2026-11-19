from datetime import timedelta

from rest_framework import serializers

from wishlist.models import Idea, WishlistItem


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
