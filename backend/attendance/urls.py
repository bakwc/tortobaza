from django.urls import path

from attendance.views import (
    AttendanceMarkView,
    AttendanceSummaryView,
    ScheduleFillView,
    ScheduleView,
    TimesheetView,
)

urlpatterns = [
    path("attendance/mark/", AttendanceMarkView.as_view(), name="attendance-mark"),
    path("attendance/summary/", AttendanceSummaryView.as_view(), name="attendance-summary"),
    path("attendance/schedule/", ScheduleView.as_view(), name="attendance-schedule"),
    path("attendance/schedule/fill/", ScheduleFillView.as_view(), name="attendance-schedule-fill"),
    path("attendance/timesheet/", TimesheetView.as_view(), name="attendance-timesheet"),
]
