from django.urls import path

from attendance.views import AttendanceMarkView

urlpatterns = [
    path("attendance/mark/", AttendanceMarkView.as_view(), name="attendance-mark"),
]
