from django.urls import path

from crm.views import CrmOrderDetailView, CrmOrderListView

urlpatterns = [
    path("crm/orders/", CrmOrderListView.as_view(), name="crm-order-list"),
    path("crm/orders/<int:pk>/", CrmOrderDetailView.as_view(), name="crm-order-detail"),
]
