from django.urls import path

from attendance.views import AttendanceMarkView, AttendanceSummaryView

urlpatterns = [
    path("attendance/mark/", AttendanceMarkView.as_view(), name="attendance-mark"),
    path("attendance/summary/", AttendanceSummaryView.as_view(), name="attendance-summary"),
]
