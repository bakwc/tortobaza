from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import get_language
from rest_framework import generics

from catalog.models import Category, Product
from catalog.serializers import (
    CategoryDetailSerializer,
    CategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)

_PAGE_SLUG_FIELDS = {
    "en": "page_slug_en",
    "ka": "page_slug_ka",
    "ru": "page_slug_ru",
}


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    pagination_class = None

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by("position", "name")


class CategoryDetailView(generics.RetrieveAPIView):
    serializer_class = CategoryDetailSerializer
    lookup_url_kwarg = "page_slug"

    def get_queryset(self):
        language = get_language() or "en"
        field = _PAGE_SLUG_FIELDS.get(language, "page_slug_en")
        return Category.objects.filter(
            is_active=True,
            **{f"{field}__isnull": False},
        ).exclude(**{field: ""})

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        page_slug = self.kwargs[self.lookup_url_kwarg]
        language = get_language() or "en"
        field = _PAGE_SLUG_FIELDS.get(language, "page_slug_en")
        obj = queryset.filter(**{field: page_slug}).first()
        if obj is None:
            obj = get_object_or_404(
                queryset,
                Q(page_slug_en=page_slug)
                | Q(page_slug_ka=page_slug)
                | Q(page_slug_ru=page_slug),
            )
        self.check_object_permissions(self.request, obj)
        return obj


class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer

    def get_queryset(self):
        qs = (
            Product.objects.filter(is_active=True, category__is_active=True)
            .select_related("category")
            .prefetch_related("images")
        )
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
            Product.objects.filter(is_active=True, category__is_active=True)
            .select_related("category")
            .prefetch_related("images", "product_option_groups__option_group__options")
        )
