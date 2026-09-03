from django.urls import path

from crm.views import (
    CrmOrderClientView,
    CrmOrderDetailView,
    CrmOrderListView,
    ResolveGoogleAddressView,
    ResolveYandexAddressView,
)

urlpatterns = [
    path("crm/orders/", CrmOrderListView.as_view(), name="crm-order-list"),
    path(
        "crm/orders/client/<str:token>/",
        CrmOrderClientView.as_view(),
        name="crm-order-client",
    ),
    path("crm/orders/<int:pk>/", CrmOrderDetailView.as_view(), name="crm-order-detail"),
    path(
        "crm/resolve-yandex-address/",
        ResolveYandexAddressView.as_view(),
        name="crm-resolve-yandex-address",
    ),
    path(
        "crm/resolve-google-address/",
        ResolveGoogleAddressView.as_view(),
        name="crm-resolve-google-address",
    ),
]
