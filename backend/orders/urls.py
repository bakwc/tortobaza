from django.urls import path

from orders.views import (
    FulfillmentOptionsView,
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
]
