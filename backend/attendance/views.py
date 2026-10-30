from datetime import timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.models import AttendanceEvent
from attendance.salary import compute_salary
from attendance.schedule import apply_pattern, month_bounds, save_cells, schedule_grid, timesheet_grid
from attendance.serializers import (
    AttendanceEventSerializer,
    AttendanceMarkInputSerializer,
    MonthQuerySerializer,
    ScheduleFillSerializer,
    ScheduleWriteSerializer,
)
from crm.views import IsFinanceAdmin

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
        result = compute_salary(request.user, start_date, end_date, None)
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


def _month_bounds_from_request(request):
    serializer = MonthQuerySerializer(data={"month": request.query_params.get("month")})
    serializer.is_valid(raise_exception=True)
    return month_bounds(serializer.validated_data["month"])


class ScheduleView(APIView):
    authentication_classes = [SessionAuthentication]

    def get_permissions(self):
        if self.request.method == "PUT":
            return [IsFinanceAdmin()]
        return [IsAuthenticated()]

    def get(self, request):
        start, end = _month_bounds_from_request(request)
        return Response(schedule_grid(start, end))

    @transaction.atomic
    def put(self, request):
        serializer = ScheduleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        save_cells(serializer.validated_data["cells"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ScheduleFillView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsFinanceAdmin]

    @transaction.atomic
    def post(self, request):
        serializer = ScheduleFillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = get_object_or_404(User, pk=data["user"])
        apply_pattern(user, data["start"], data["end"], data["cycle_start"], data["pattern"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class TimesheetView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsFinanceAdmin]

    def get(self, request):
        start, end = _month_bounds_from_request(request)
        today = timezone.now().astimezone(_TB).date()
        return Response(timesheet_grid(start, end, today))
