from django.contrib import admin

from crm.models import CrmOrder, CrmOrderImage
from crm.telegram import schedule_crm_order_telegram_sync


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
        "nickname",
        "fulfillment_type",
        "is_delivered",
        "weight",
        "filling",
        "cake_price",
        "prepayment",
        "is_paid",
        "payment_type",
        "deleted",
    ]
    list_display_links = ["id", "date"]
    list_filter = ["date", "fulfillment_type", "is_delivered", "is_paid", "payment_type", "deleted"]
    search_fields = ["id", "contact", "nickname", "delivery_address", "filling", "description", "weight"]
    date_hierarchy = "date"
    inlines = [CrmOrderImageInline]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "telegram_message_id",
        "telegram_media_ids",
        "telegram_payload_hash",
        "telegram_posted_date",
        "telegram_posted_time_start",
        "telegram_posted_time_end",
    ]
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
                "fields": ("contact", "nickname", "delivery_address", "fulfillment_type", "is_delivered"),
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
                "fields": ("id", "deleted", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "Telegram",
            {
                "fields": (
                    "telegram_message_id",
                    "telegram_media_ids",
                    "telegram_payload_hash",
                    "telegram_posted_date",
                    "telegram_posted_time_start",
                    "telegram_posted_time_end",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Time")
    def time_slot(self, obj: CrmOrder) -> str:
        if obj.time_start is None:
            return "Unknown"
        if obj.time_end:
            return f"{obj.time_start.strftime('%H:%M')} – {obj.time_end.strftime('%H:%M')}"
        return obj.time_start.strftime("%H:%M")

    @admin.display(description="Contact")
    def contact_summary(self, obj: CrmOrder) -> str:
        return obj.contact[:50]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        schedule_crm_order_telegram_sync(form.instance.pk)
