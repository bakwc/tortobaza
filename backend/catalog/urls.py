from django.urls import path

from catalog.img_view import scaled_image
from catalog.views import CategoryListView, ProductDetailView, ProductListView

urlpatterns = [
    path("img/<path:relative_path>", scaled_image, name="scaled-image"),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
]
