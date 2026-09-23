from django.urls import path

from crm.views import (
    CrmExpensesView,
    CrmOrderClientMapView,
    CrmOrderClientView,
    CrmOrderDetailView,
    CrmOrderEventsView,
    CrmOrderListView,
    CrmOrderMapView,
    FlowwowWebhookView,
    ResolveGoogleAddressView,
    ResolveYandexAddressView,
)

urlpatterns = [
    path("webhooks/flowwow/", FlowwowWebhookView.as_view(), name="flowwow-webhook"),
    path("crm/expenses/", CrmExpensesView.as_view(), name="crm-expenses"),
    path("crm/orders/map/", CrmOrderMapView.as_view(), name="crm-order-map"),
    path("crm/orders/", CrmOrderListView.as_view(), name="crm-order-list"),
    path(
        "crm/orders/client/<str:token>/map/",
        CrmOrderClientMapView.as_view(),
        name="crm-order-client-map",
    ),
    path(
        "crm/orders/client/<str:token>/",
        CrmOrderClientView.as_view(),
        name="crm-order-client",
    ),
    path("crm/orders/<int:pk>/", CrmOrderDetailView.as_view(), name="crm-order-detail"),
    path("crm/orders/<int:pk>/events/", CrmOrderEventsView.as_view(), name="crm-order-events"),
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
