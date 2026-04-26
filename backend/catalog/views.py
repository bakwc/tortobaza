from django.db.models import Q
from rest_framework import generics

from catalog.models import Category, Product
from catalog.serializers import (
    CategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    pagination_class = None

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by("position", "name")


class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related("category").prefetch_related("images")
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__slug=category)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs.order_by("position", "-created_at")


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("images", "product_option_groups__option_group__options")
        )
