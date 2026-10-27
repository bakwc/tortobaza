from django.urls import path

from rsge.views import (
    InvoiceConfirmView,
    InvoiceListView,
    InvoiceRejectView,
    PendingCountView,
    WaybillConfirmView,
    WaybillListView,
    WaybillRejectView,
)

urlpatterns = [
    path("rsge/pending-count/", PendingCountView.as_view()),
    path("rsge/waybills/", WaybillListView.as_view()),
    path("rsge/waybills/<int:pk>/confirm/", WaybillConfirmView.as_view()),
    path("rsge/waybills/<int:pk>/reject/", WaybillRejectView.as_view()),
    path("rsge/invoices/", InvoiceListView.as_view()),
    path("rsge/invoices/<int:pk>/confirm/", InvoiceConfirmView.as_view()),
    path("rsge/invoices/<int:pk>/reject/", InvoiceRejectView.as_view()),
]
