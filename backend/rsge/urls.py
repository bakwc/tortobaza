from django.urls import path

from rsge.views import WaybillListView

urlpatterns = [
    path("rsge/waybills/", WaybillListView.as_view()),
]
