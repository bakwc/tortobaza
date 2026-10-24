from django.urls import path

from rsge.views import InvoiceListView, WaybillListView

urlpatterns = [
    path("rsge/waybills/", WaybillListView.as_view()),
    path("rsge/invoices/", InvoiceListView.as_view()),
]
