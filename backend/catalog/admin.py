from django.contrib import admin

from catalog.models import (
    Category,
    Option,
    OptionGroup,
    Product,
    ProductImage,
    ProductOptionGroup,
)


class OptionInline(admin.TabularInline):
    model = Option
    extra = 1
    fields = ["name", "image", "price_delta", "position", "is_active"]


@admin.register(OptionGroup)
class OptionGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "selection_type", "is_required_default"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [OptionInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "position", "is_active"]
    list_editable = ["position", "is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "alt", "position"]


class ProductOptionGroupInline(admin.TabularInline):
    model = ProductOptionGroup
    extra = 1
    fields = ["option_group", "position", "is_required"]
    autocomplete_fields = ["option_group"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "base_price", "position", "is_active", "created_at"]
    list_filter = ["category", "is_active"]
    list_editable = ["position", "is_active"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline, ProductOptionGroupInline]
