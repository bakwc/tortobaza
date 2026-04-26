from django.contrib import admin

from cart.models import Cart, CartItem, CartItemOption


class CartItemOptionInline(admin.TabularInline):
    model = CartItemOption
    extra = 0


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ["product", "quantity", "comment", "added_at"]
    readonly_fields = ["added_at"]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["token", "is_ordered", "created_at", "updated_at", "expires_at"]
    list_filter = ["is_ordered"]
    search_fields = ["token"]
    readonly_fields = ["token", "created_at", "updated_at"]
    inlines = [CartItemInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["id", "cart", "product", "quantity", "added_at"]
    list_filter = ["product"]
    inlines = [CartItemOptionInline]
