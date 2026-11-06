from django.urls import path

from audit.views import AuditActorsView, AuditEventsView

urlpatterns = [
    path("audit/actors/", AuditActorsView.as_view(), name="audit-actors"),
    path("audit/events/", AuditEventsView.as_view(), name="audit-events"),
]
