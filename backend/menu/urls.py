from django.urls import path

from menu.views import (
    CatalogOptionListView,
    IngredientCategoryDetailView,
    IngredientCategoryListView,
    IngredientDetailView,
    IngredientListView,
    MissingModifierLinesView,
    ModifierGroupDetailView,
    ModifierGroupListView,
    SemiProductDetailView,
    SemiProductListView,
    TechCardCostView,
    TechCardDetailView,
    TechCardListView,
)

urlpatterns = [
    path("menu/ingredient-categories/", IngredientCategoryListView.as_view()),
    path("menu/ingredient-categories/<int:pk>/", IngredientCategoryDetailView.as_view()),
    path("menu/ingredients/", IngredientListView.as_view()),
    path("menu/ingredients/<int:pk>/", IngredientDetailView.as_view()),
    path("menu/semi-products/", SemiProductListView.as_view()),
    path("menu/semi-products/<int:pk>/", SemiProductDetailView.as_view()),
    path("menu/modifier-groups/", ModifierGroupListView.as_view()),
    path("menu/modifier-groups/<int:pk>/", ModifierGroupDetailView.as_view()),
    path("menu/tech-cards/", TechCardListView.as_view()),
    path("menu/tech-cards/<int:pk>/", TechCardDetailView.as_view()),
    path("menu/tech-cards/<int:pk>/cost/", TechCardCostView.as_view()),
    path("menu/missing-modifier-lines/", MissingModifierLinesView.as_view()),
    path("menu/catalog-options/", CatalogOptionListView.as_view()),
]
