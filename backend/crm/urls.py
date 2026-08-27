from django.urls import path

from crm.views import CrmOrderDetailView, CrmOrderListView, ResolveYandexAddressView

urlpatterns = [
    path("crm/orders/", CrmOrderListView.as_view(), name="crm-order-list"),
    path("crm/orders/<int:pk>/", CrmOrderDetailView.as_view(), name="crm-order-detail"),
    path(
        "crm/resolve-yandex-address/",
        ResolveYandexAddressView.as_view(),
        name="crm-resolve-yandex-address",
    ),
]
