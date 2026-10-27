from django.urls import path

from audit.views import AuditEventsView

urlpatterns = [
    path("audit/events/", AuditEventsView.as_view(), name="audit-events"),
]
