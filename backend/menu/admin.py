from django.contrib import admin

from menu.models import (
    Ingredient,
    IngredientCategory,
    Modifier,
    ModifierGroup,
    SemiProduct,
    SemiProductLine,
    TechCard,
    TechCardCategory,
    TechCardLine,
    TechCardModifierGroup,
    TechCardModifierLine,
)


@admin.register(IngredientCategory)
class IngredientCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "position"]
    list_editable = ["position"]
    search_fields = ["name"]


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "unit", "avg_cost", "is_active"]
    list_filter = ["category", "unit", "is_active"]
    search_fields = ["name"]
    readonly_fields = ["avg_cost"]


class SemiProductLineInline(admin.TabularInline):
    model = SemiProductLine
    fk_name = "parent"
    extra = 1
    fields = ["ingredient", "semi_product", "quantity", "loss_percent", "position"]
    autocomplete_fields = ["ingredient", "semi_product"]


@admin.register(SemiProduct)
class SemiProductAdmin(admin.ModelAdmin):
    list_display = ["name", "unit", "yield_quantity", "is_produced", "avg_cost", "is_active"]
    list_filter = ["is_produced", "is_active"]
    search_fields = ["name"]
    readonly_fields = ["avg_cost"]
    inlines = [SemiProductLineInline]


class ModifierInline(admin.TabularInline):
    model = Modifier
    extra = 1
    fields = ["name", "catalog_option", "position", "is_active"]


@admin.register(ModifierGroup)
class ModifierGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "selection_type", "is_required", "min_selections", "max_selections", "position"]
    search_fields = ["name"]
    inlines = [ModifierInline]


@admin.register(Modifier)
class ModifierAdmin(admin.ModelAdmin):
    list_display = ["name", "group", "catalog_option", "is_active"]
    list_filter = ["group", "is_active"]
    search_fields = ["name", "group__name"]


class TechCardLineInline(admin.TabularInline):
    model = TechCardLine
    extra = 1
    fields = ["ingredient", "semi_product", "quantity", "loss_percent", "position"]
    autocomplete_fields = ["ingredient", "semi_product"]


class TechCardModifierGroupInline(admin.TabularInline):
    model = TechCardModifierGroup
    extra = 1
    fields = ["group", "is_required", "position"]


class TechCardModifierLineInline(admin.TabularInline):
    model = TechCardModifierLine
    extra = 1
    fields = ["modifier", "ingredient", "semi_product", "quantity", "loss_percent", "scales_by_weight", "position"]
    autocomplete_fields = ["modifier", "ingredient", "semi_product"]


@admin.register(TechCardCategory)
class TechCardCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "position"]
    list_editable = ["position"]
    search_fields = ["name"]


@admin.register(TechCard)
class TechCardAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "kind", "is_active", "created_at"]
    list_filter = ["category", "kind", "is_active"]
    search_fields = ["name"]
    inlines = [TechCardLineInline, TechCardModifierGroupInline, TechCardModifierLineInline]
