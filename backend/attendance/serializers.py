from django.contrib.auth.models import User
from rest_framework import serializers

from attendance.models import AttendanceEvent, ScheduleDay


class AttendanceEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceEvent
        fields = ["id", "user", "event_type", "timestamp"]


class AttendanceMarkInputSerializer(serializers.Serializer):
    event_type = serializers.ChoiceField(choices=AttendanceEvent.EVENT_TYPE_CHOICES)


class MonthQuerySerializer(serializers.Serializer):
    month = serializers.CharField()

    def validate_month(self, value: str) -> str:
        parts = value.split("-")
        if (
            len(parts) != 2
            or len(parts[0]) != 4
            or not parts[0].isdigit()
            or len(parts[1]) != 2
            or not parts[1].isdigit()
        ):
            raise serializers.ValidationError("Invalid month.")
        month_number = int(parts[1])
        if month_number < 1 or month_number > 12:
            raise serializers.ValidationError("Invalid month.")
        return value


class ScheduleCellSerializer(serializers.Serializer):
    user = serializers.IntegerField()
    date = serializers.DateField()
    day_type = serializers.ChoiceField(choices=ScheduleDay.DAY_TYPE_CHOICES, allow_null=True)


class ScheduleWriteSerializer(serializers.Serializer):
    cells = ScheduleCellSerializer(many=True)

    def validate(self, attrs):
        ids = {cell["user"] for cell in attrs["cells"]}
        found = set(User.objects.filter(pk__in=ids).values_list("pk", flat=True))
        if ids != found:
            raise serializers.ValidationError({"cells": ["Unknown user."]})
        return attrs


class ScheduleFillSerializer(serializers.Serializer):
    user = serializers.IntegerField()
    start = serializers.DateField()
    end = serializers.DateField()
    cycle_start = serializers.DateField()
    pattern = serializers.ListField(
        child=serializers.ChoiceField(choices=ScheduleDay.DAY_TYPE_CHOICES),
        allow_empty=False,
    )

    def validate(self, attrs):
        if attrs["end"] < attrs["start"]:
            raise serializers.ValidationError({"end": ["End is before start."]})
        return attrs
