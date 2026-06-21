from django.contrib import admin

from attendance.models import AttendanceEvent


@admin.register(AttendanceEvent)
class AttendanceEventAdmin(admin.ModelAdmin):
    list_display = ["user", "event_type", "timestamp"]
    list_filter = ["event_type", "user"]
    date_hierarchy = "timestamp"
    search_fields = ["user__username"]
    readonly_fields = ["timestamp"]
