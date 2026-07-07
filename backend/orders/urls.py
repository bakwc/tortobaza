from django.urls import path

from orders.views import (
    FulfillmentOptionsView,
    LibertyCallbackView,
    LibertyPaymentStartView,
    OrderCreateView,
    OrderDetailView,
    OrderPreviewView,
    PickupLocationListView,
    PromoCodeValidateView,
)

urlpatterns = [
    path("pickup-locations/", PickupLocationListView.as_view(), name="pickup-locations"),
    path("fulfillment-options/", FulfillmentOptionsView.as_view(), name="fulfillment-options"),
    path("promo-codes/validate/", PromoCodeValidateView.as_view(), name="promo-validate"),
    path("orders/preview/", OrderPreviewView.as_view(), name="orders-preview"),
    path("orders/", OrderCreateView.as_view(), name="orders-create"),
    path("orders/<str:number>/", OrderDetailView.as_view(), name="orders-detail"),
    path("payments/liberty/start/", LibertyPaymentStartView.as_view(), name="liberty-payment-start"),
    path("payments/liberty/callback/", LibertyCallbackView.as_view(), name="liberty-payment-callback"),
]
