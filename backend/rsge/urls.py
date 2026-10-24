from django.urls import path

from rsge.views import InvoiceListView, WaybillConfirmView, WaybillListView, WaybillRejectView

urlpatterns = [
    path("rsge/waybills/", WaybillListView.as_view()),
    path("rsge/waybills/<int:pk>/confirm/", WaybillConfirmView.as_view()),
    path("rsge/waybills/<int:pk>/reject/", WaybillRejectView.as_view()),
    path("rsge/invoices/", InvoiceListView.as_view()),
]
