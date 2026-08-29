from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import get_language
from rest_framework import generics, status
from rest_framework.response import Response

from catalog.models import Category, CategoryLanding, Product
from catalog.serializers import (
    CategoryDetailSerializer,
    CategoryLandingDetailSerializer,
    CategoryLandingListSerializer,
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


class CategoryLandingListView(generics.ListAPIView):
    serializer_class = CategoryLandingListSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            CategoryLanding.objects.filter(is_active=True, source__is_active=True)
            .select_related("source")
            .order_by("slug")
        )


class CategoryDetailView(generics.RetrieveAPIView):
    lookup_url_kwarg = "page_slug"

    def get_object(self):
        page_slug = self.kwargs[self.lookup_url_kwarg]
        language = get_language() or "en"
        field = _PAGE_SLUG_FIELDS.get(language, "page_slug_en")

        categories = Category.objects.filter(
            is_active=True,
            **{f"{field}__isnull": False},
        ).exclude(**{field: ""})

        obj = categories.filter(**{field: page_slug}).first()
        if obj is None:
            obj = Category.objects.filter(
                is_active=True,
            ).filter(
                Q(page_slug_en=page_slug)
                | Q(page_slug_ka=page_slug)
                | Q(page_slug_ru=page_slug),
            ).first()

        if obj is None:
            landings = CategoryLanding.objects.filter(
                is_active=True,
                source__is_active=True,
                **{f"{field}__isnull": False},
            ).exclude(**{field: ""}).select_related("source")

            obj = landings.filter(**{field: page_slug}).first()
            if obj is None:
                obj = get_object_or_404(
                    CategoryLanding.objects.filter(
                        is_active=True,
                        source__is_active=True,
                    ).select_related("source"),
                    Q(page_slug_en=page_slug)
                    | Q(page_slug_ka=page_slug)
                    | Q(page_slug_ru=page_slug),
                )

        self._resolved_obj = obj
        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer(self, *args, **kwargs):
        if len(args) > 0 and isinstance(args[0], CategoryLanding):
            serializer_class = CategoryLandingDetailSerializer
        elif hasattr(self, "_resolved_obj") and isinstance(self._resolved_obj, CategoryLanding):
            serializer_class = CategoryLandingDetailSerializer
        else:
            serializer_class = CategoryDetailSerializer
        kwargs.setdefault("context", self.get_serializer_context())
        return serializer_class(*args, **kwargs)


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

    def retrieve(self, request, *args, **kwargs):
        slug = self.kwargs[self.lookup_field]
        product = self.get_queryset().filter(slug=slug).first()
        if product is not None:
            return Response(self.get_serializer(product).data)

        gone = Product.objects.filter(slug=slug).select_related("category").first()
        if gone is None:
            raise Http404

        category_page_slug = None
        if gone.category.is_active:
            language = get_language() or "en"
            field = _PAGE_SLUG_FIELDS.get(language, "page_slug_en")
            category_page_slug = getattr(gone.category, field) or None
        return Response(
            {"detail": "gone", "category_page_slug": category_page_slug},
            status=status.HTTP_410_GONE,
        )
