from django.urls import path

from wishlist.views import IdeaDetailView, IdeaListView, WishlistDetailView, WishlistListView

urlpatterns = [
    path("wishlist/", WishlistListView.as_view()),
    path("wishlist/ideas/", IdeaListView.as_view()),
    path("wishlist/ideas/<int:pk>/", IdeaDetailView.as_view()),
    path("wishlist/<int:pk>/", WishlistDetailView.as_view()),
]
