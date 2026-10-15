from django.contrib import admin

from inventory.models import (
    InventoryCount,
    InventoryCountLine,
    Production,
    StockMovement,
    Supplier,
    Supply,
    SupplyLine,
    WriteOff,
    WriteOffLine,
    WriteOffReason,
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "phone"]
    search_fields = ["name", "phone"]


@admin.register(WriteOffReason)
class WriteOffReasonAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


class SupplyLineInline(admin.TabularInline):
    model = SupplyLine
    extra = 0
    fields = ["ingredient", "quantity", "total"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    list_display = ["id", "date", "supplier", "financial_transaction", "created_by"]
    list_filter = ["date", "supplier"]
    readonly_fields = ["date", "supplier", "financial_transaction", "comment", "created_by", "created_at"]
    inlines = [SupplyLineInline]

    def has_add_permission(self, request):
        return False


@admin.register(Production)
class ProductionAdmin(admin.ModelAdmin):
    list_display = ["id", "date", "semi_product", "quantity", "created_by"]
    list_filter = ["date", "semi_product"]
    readonly_fields = ["date", "semi_product", "quantity", "comment", "created_by", "created_at"]

    def has_add_permission(self, request):
        return False


class WriteOffLineInline(admin.TabularInline):
    model = WriteOffLine
    extra = 0
    fields = ["ingredient", "semi_product", "quantity"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(WriteOff)
class WriteOffAdmin(admin.ModelAdmin):
    list_display = ["id", "date", "reason", "created_by"]
    list_filter = ["date", "reason"]
    readonly_fields = ["date", "reason", "comment", "created_by", "created_at"]
    inlines = [WriteOffLineInline]

    def has_add_permission(self, request):
        return False


class InventoryCountLineInline(admin.TabularInline):
    model = InventoryCountLine
    extra = 0
    fields = ["ingredient", "semi_product", "expected_quantity", "actual_quantity", "unit_cost"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(InventoryCount)
class InventoryCountAdmin(admin.ModelAdmin):
    list_display = ["id", "date", "status", "created_by", "closed_at"]
    list_filter = ["status", "date"]
    readonly_fields = ["date", "status", "comment", "created_by", "created_at", "closed_at"]
    inlines = [InventoryCountLineInline]

    def has_add_permission(self, request):
        return False


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["id", "date", "kind", "ingredient", "semi_product", "quantity", "unit_cost", "crm_order"]
    list_filter = ["kind", "date"]
    search_fields = ["ingredient__name", "semi_product__name"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
