from django.urls import path

from orders.views import (
    DeliveryTimeslotListView,
    OrderCreateView,
    OrderDetailView,
    OrderPreviewView,
    PickupLocationListView,
    PromoCodeValidateView,
)

urlpatterns = [
    path("pickup-locations/", PickupLocationListView.as_view(), name="pickup-locations"),
    path("delivery-timeslots/", DeliveryTimeslotListView.as_view(), name="delivery-timeslots"),
    path("promo-codes/validate/", PromoCodeValidateView.as_view(), name="promo-validate"),
    path("orders/preview/", OrderPreviewView.as_view(), name="orders-preview"),
    path("orders/", OrderCreateView.as_view(), name="orders-create"),
    path("orders/<str:number>/", OrderDetailView.as_view(), name="orders-detail"),
]
