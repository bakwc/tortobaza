from rest_framework import serializers

from attendance.models import AttendanceEvent


class AttendanceEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceEvent
        fields = ["id", "user", "event_type", "timestamp"]


class AttendanceMarkInputSerializer(serializers.Serializer):
    event_type = serializers.ChoiceField(choices=AttendanceEvent.EVENT_TYPE_CHOICES)
