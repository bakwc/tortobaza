from django.urls import path

from wishlist.views import WishlistDetailView, WishlistListView

urlpatterns = [
    path("wishlist/", WishlistListView.as_view()),
    path("wishlist/<int:pk>/", WishlistDetailView.as_view()),
]
