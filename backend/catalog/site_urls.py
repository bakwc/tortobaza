from django.urls import path

from catalog.site_views import (
    SiteCategoryDetailView,
    SiteCategoryImageView,
    SiteCategoryLandingDetailView,
    SiteCategoryLandingImageView,
    SiteCategoryLandingListView,
    SiteCategoryListView,
    SiteTranslationView,
    SiteOptionGroupDetailView,
    SiteOptionGroupListView,
    SiteOptionImageView,
    SiteProductDetailView,
    SiteProductImageCreateView,
    SiteProductImageDetailView,
    SiteProductImageReorderView,
    SiteProductListView,
    SiteTechCardChoicesView,
)

urlpatterns = [
    path("site/categories/", SiteCategoryListView.as_view()),
    path("site/categories/<int:pk>/", SiteCategoryDetailView.as_view()),
    path("site/categories/<int:pk>/image/", SiteCategoryImageView.as_view()),
    path("site/category-landings/", SiteCategoryLandingListView.as_view()),
    path("site/category-landings/<int:pk>/", SiteCategoryLandingDetailView.as_view()),
    path("site/category-landings/<int:pk>/image/", SiteCategoryLandingImageView.as_view()),
    path("site/option-groups/", SiteOptionGroupListView.as_view()),
    path("site/option-groups/<int:pk>/", SiteOptionGroupDetailView.as_view()),
    path("site/options/<int:pk>/image/", SiteOptionImageView.as_view()),
    path("site/products/", SiteProductListView.as_view()),
    path("site/products/<int:pk>/", SiteProductDetailView.as_view()),
    path("site/products/<int:pk>/images/", SiteProductImageCreateView.as_view()),
    path("site/products/<int:pk>/images/reorder/", SiteProductImageReorderView.as_view()),
    path("site/products/<int:pk>/images/<int:image_pk>/", SiteProductImageDetailView.as_view()),
    path("site/tech-cards/", SiteTechCardChoicesView.as_view()),
    path("site/translate/", SiteTranslationView.as_view()),
]
