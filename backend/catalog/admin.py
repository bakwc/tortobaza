from django.contrib import admin
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline

from catalog.models import (
    Category,
    CategoryLanding,
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
    list_display = ["name", "slug", "selection_type", "min_selections", "max_selections", "is_required_default"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [OptionInline]


@admin.register(Category)
class CategoryAdmin(TranslationAdmin):
    list_display = ["name", "slug", "page_slug", "delivery_schedule_tier", "position", "is_active"]
    list_editable = ["position", "is_active"]
    list_filter = ["delivery_schedule_tier", "is_active"]
    search_fields = ["name", "slug", "page_slug"]
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "slug",
                    "page_slug",
                    "page_heading",
                    "page_description",
                    "image",
                    "delivery_schedule_tier",
                    "position",
                    "is_active",
                )
            },
        ),
        (
            "SEO",
            {
                "fields": ("seo_title", "seo_description"),
            },
        ),
    )


@admin.register(CategoryLanding)
class CategoryLandingAdmin(TranslationAdmin):
    list_display = ["slug", "source", "page_slug", "is_active", "updated_at"]
    list_filter = ["is_active", "source"]
    search_fields = ["slug", "page_slug", "page_heading"]
    autocomplete_fields = ["source"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "slug",
                    "source",
                    "page_slug",
                    "page_heading",
                    "page_description",
                    "image",
                    "is_active",
                )
            },
        ),
        (
            "SEO",
            {
                "fields": ("seo_title", "seo_description"),
            },
        ),
    )


class ProductImageInline(TranslationTabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "alt", "position"]


class ProductOptionGroupInline(admin.TabularInline):
    model = ProductOptionGroup
    extra = 1
    fields = ["option_group", "position", "is_required"]
    autocomplete_fields = ["option_group"]


@admin.register(Product)
class ProductAdmin(TranslationAdmin):
    list_display = [
        "name",
        "category",
        "delivery_schedule_tier",
        "base_price",
        "position",
        "is_active",
        "created_at",
    ]
    list_filter = ["category", "delivery_schedule_tier", "is_active"]
    list_editable = ["position", "is_active"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline, ProductOptionGroupInline]
