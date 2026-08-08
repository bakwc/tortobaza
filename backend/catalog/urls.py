from django.urls import path

from catalog.feed_view import meta_product_feed
from catalog.img_view import scaled_image
from catalog.views import (
    CategoryDetailView,
    CategoryListView,
    ProductDetailView,
    ProductListView,
)

urlpatterns = [
    path("feed/meta.xml", meta_product_feed, name="meta-product-feed"),
    path("img/<path:relative_path>", scaled_image, name="scaled-image"),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/<slug:page_slug>/", CategoryDetailView.as_view(), name="category-detail"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
]
