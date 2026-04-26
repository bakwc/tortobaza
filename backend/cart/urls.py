from django.urls import path

from cart.views import CartItemDetailView, CartItemListView, CartView

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemListView.as_view(), name="cart-items"),
    path("cart/items/<int:item_id>/", CartItemDetailView.as_view(), name="cart-item-detail"),
]
