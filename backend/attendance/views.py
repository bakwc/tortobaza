from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.models import AttendanceEvent
from attendance.serializers import AttendanceEventSerializer, AttendanceMarkInputSerializer


class AttendanceMarkView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AttendanceMarkInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = AttendanceEvent.objects.create(
            user=request.user,
            event_type=serializer.validated_data["event_type"],
        )
        return Response(
            AttendanceEventSerializer(event).data,
            status=status.HTTP_201_CREATED,
        )
