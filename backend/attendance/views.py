from datetime import timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.models import AttendanceEvent
from attendance.salary import compute_salary
from attendance.serializers import AttendanceEventSerializer, AttendanceMarkInputSerializer

_TB = ZoneInfo("Asia/Tbilisi")


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


class AttendanceSummaryView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        end_date = timezone.now().astimezone(_TB).date()
        start_date = end_date - timedelta(days=14)
        result = compute_salary(request.user, start_date, end_date)
        rows = [
            {
                "date": row["date"].isoformat(),
                "arrival": row["arrival"].isoformat() if row["arrival"] else None,
                "departure": row["departure"].isoformat() if row["departure"] else None,
                "hours": str(row["hours"]),
                "money": str(row["money"]),
            }
            for row in reversed(result["rows"])
        ]
        return Response(
            {
                "hourly_rate": str(result["hourly_rate"]),
                "rows": rows,
                "total_hours": str(result["total_hours"]),
                "total_money": str(result["total_money"]),
            }
        )
