from django import forms
from django.contrib import admin
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from crm.flowwow import sync_flowwow_order_status_from_crm
from crm.models import CrmOrder, CrmOrderImage, CrmSettings, WhatsAppGetNewQr, WhatsAppNumberCheck
from crm.telegram import schedule_crm_order_telegram_sync
from crm.website import sync_website_order_status_from_crm
from crm.whatsapp import check_number, get_new_qr


class WhatsAppNumberCheckForm(forms.Form):
    number = forms.CharField()


@admin.register(CrmSettings)
class CrmSettingsAdmin(admin.ModelAdmin):
    fields = ["monthly_rent"]

    def has_add_permission(self, request):
        return not CrmSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = CrmSettings.load()
        return redirect(reverse("admin:crm_crmsettings_change", args=[obj.pk]))


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
        "status",
        "taken_by",
        "created_by",
        "weight",
        "filling",
        "cake_price",
        "prepayment",
        "is_paid",
        "payment_type",
        "deleted",
    ]
    list_display_links = ["id", "date"]
    list_filter = ["date", "fulfillment_type", "status", "is_paid", "payment_type", "deleted"]
    search_fields = ["id", "contact", "nickname", "delivery_address", "filling", "description", "internal_description", "weight"]
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
        "telegram_posted_when_ready",
    ]
    fieldsets = (
        (
            "Schedule",
            {
                "fields": ("date", "time_start", "time_end", "when_ready"),
            },
        ),
        (
            "Customer & Delivery",
            {
                "fields": (
                    "contact",
                    "nickname",
                    "delivery_address",
                    "fulfillment_type",
                    "status",
                    "taken_by",
                    "created_by",
                ),
            },
        ),
        (
            "Cake Details",
            {
                "fields": ("weight", "filling", "description", "internal_description"),
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
                    "telegram_posted_when_ready",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Time")
    def time_slot(self, obj: CrmOrder) -> str:
        if obj.when_ready:
            return "When ready"
        if obj.time_start is None:
            return "Unknown"
        if obj.time_end:
            return f"{obj.time_start.strftime('%H:%M')} – {obj.time_end.strftime('%H:%M')}"
        return obj.time_start.strftime("%H:%M")

    @admin.display(description="Contact")
    def contact_summary(self, obj: CrmOrder) -> str:
        return obj.contact[:50]

    def save_model(self, request, obj, form, change):
        if change:
            sync_flowwow_order_status_from_crm(obj, form.initial["status"])
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        sync_website_order_status_from_crm(form.instance)
        schedule_crm_order_telegram_sync(form.instance.pk)


@admin.register(WhatsAppNumberCheck)
class WhatsAppNumberCheckAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        form = WhatsAppNumberCheckForm(request.GET or None)
        result = None
        if form.is_valid():
            result = check_number(form.cleaned_data["number"])

        context = {
            **self.admin_site.each_context(request),
            "title": "WhatsApp number check",
            "form": form,
            "result": result,
            "opts": self.model._meta,
            "cl": {"opts": self.model._meta},
        }
        if extra_context:
            context.update(extra_context)

        return TemplateResponse(
            request,
            "admin/crm/whatsappnumbercheck/change_list.html",
            context,
        )


@admin.register(WhatsAppGetNewQr)
class WhatsAppGetNewQrAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        result = None
        if request.method == "POST":
            result = get_new_qr()

        context = {
            **self.admin_site.each_context(request),
            "title": "WhatsApp get new QR",
            "result": result,
            "opts": self.model._meta,
            "cl": {"opts": self.model._meta},
        }
        if extra_context:
            context.update(extra_context)

        return TemplateResponse(
            request,
            "admin/crm/whatsappgetnewqr/change_list.html",
            context,
        )
