from django.contrib import admin

from crm.models import CrmOrder, CrmOrderImage


class CrmOrderImageInline(admin.TabularInline):
    model = CrmOrderImage
    extra = 1
    fields = ["image", "position"]


@admin.register(CrmOrder)
class CrmOrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "date",
        "time_slot",
        "contact_summary",
        "fulfillment_type",
        "is_delivered",
        "weight",
        "filling",
        "cake_price",
        "prepayment",
        "is_paid",
        "payment_type",
    ]
    list_display_links = ["id", "date"]
    list_filter = ["date", "fulfillment_type", "is_delivered", "is_paid", "payment_type"]
    search_fields = ["id", "contact", "filling", "description", "weight"]
    date_hierarchy = "date"
    inlines = [CrmOrderImageInline]
    readonly_fields = ["id", "created_at", "updated_at"]
    fieldsets = (
        (
            "Schedule",
            {
                "fields": ("date", "time_start", "time_end"),
            },
        ),
        (
            "Customer & Delivery",
            {
                "fields": ("contact", "fulfillment_type", "is_delivered"),
            },
        ),
        (
            "Cake Details",
            {
                "fields": ("weight", "filling", "description"),
            },
        ),
        (
            "Payment",
            {
                "fields": ("cake_price", "prepayment", "is_paid", "payment_type"),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("id", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Time")
    def time_slot(self, obj: CrmOrder) -> str:
        if obj.time_end:
            return f"{obj.time_start.strftime('%H:%M')} – {obj.time_end.strftime('%H:%M')}"
        return obj.time_start.strftime("%H:%M")

    @admin.display(description="Contact")
    def contact_summary(self, obj: CrmOrder) -> str:
        return obj.contact[:50]
