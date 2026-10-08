from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from crm.bog_statement import import_bog_statement
from crm.flowwow import sync_flowwow_order_status_from_crm
from crm.flowwow_statement import import_flowwow_statement
from crm.history import record_crm_order_event, snapshot_crm_order
from crm.liberty_statement import import_liberty_statement
from crm.models import (
    CrmOrder,
    CrmOrderEvent,
    CrmOrderImage,
    CrmSettings,
    FinancialAccount,
    FinancialTransaction,
    ResolvedTelegramPhone,
    TelegramNumberCheck,
    WhatsAppGetNewQr,
    WhatsAppNumberCheck,
)
from crm.telegram import schedule_crm_order_telegram_sync
from crm.telegram_user import resolve_phone
from crm.website import sync_website_order_status_from_crm
from orders.email import schedule_order_confirmed_email
from crm.whatsapp import check_number, get_new_qr


class WhatsAppNumberCheckForm(forms.Form):
    number = forms.CharField(label=_("Number"))


class TelegramNumberCheckForm(forms.Form):
    number = forms.CharField(label=_("Number"))


class BogStatementUploadForm(forms.Form):
    file = forms.FileField(label=_("File"))


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
        "delivered_by",
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
            _("Schedule"),
            {
                "fields": ("date", "time_start", "time_end", "when_ready"),
            },
        ),
        (
            _("Customer & Delivery"),
            {
                "fields": (
                    "contact",
                    "nickname",
                    "delivery_address",
                    "fulfillment_type",
                    "status",
                    "taken_by",
                    "created_by",
                    "delivered_by",
                ),
            },
        ),
        (
            _("Cake Details"),
            {
                "fields": ("weight", "filling", "description", "internal_description"),
            },
        ),
        (
            _("Payment"),
            {
                "fields": ("cake_price", "prepayment", "is_paid", "payment_type", "payment_date"),
            },
        ),
        (
            _("Metadata"),
            {
                "fields": ("id", "deleted", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Telegram"),
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

    @admin.display(description=_("Time"))
    def time_slot(self, obj: CrmOrder) -> str:
        if obj.when_ready:
            return _("When ready")
        if obj.time_start is None:
            return _("Unknown")
        if obj.time_end:
            return f"{obj.time_start.strftime('%H:%M')} – {obj.time_end.strftime('%H:%M')}"
        return obj.time_start.strftime("%H:%M")

    @admin.display(description=_("Contact"))
    def contact_summary(self, obj: CrmOrder) -> str:
        return obj.contact[:50]

    def save_model(self, request, obj, form, change):
        if change:
            request.crm_order_event_before = snapshot_crm_order(CrmOrder.objects.get(pk=obj.pk))
            sync_flowwow_order_status_from_crm(obj, form.initial["status"])
        else:
            request.crm_order_event_before = None
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        action = (
            CrmOrderEvent.ACTION_CREATED
            if request.crm_order_event_before is None
            else CrmOrderEvent.ACTION_UPDATED
        )
        record_crm_order_event(
            form.instance,
            action,
            CrmOrderEvent.SOURCE_ADMIN,
            request.user,
            request.crm_order_event_before,
        )
        sync_website_order_status_from_crm(form.instance)
        schedule_crm_order_telegram_sync(form.instance.pk)
        if request.crm_order_event_before is not None:
            schedule_order_confirmed_email(
                form.instance,
                request.crm_order_event_before["status"],
            )


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
            "title": _("WhatsApp number check"),
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
            "title": _("WhatsApp get new QR"),
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


@admin.register(ResolvedTelegramPhone)
class ResolvedTelegramPhoneAdmin(admin.ModelAdmin):
    list_display = ["number", "resolved", "user_id", "username", "checked_at"]
    search_fields = ["number"]
    list_filter = ["resolved"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TelegramNumberCheck)
class TelegramNumberCheckAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        form = TelegramNumberCheckForm(request.GET or None)
        result = None
        if form.is_valid():
            result = resolve_phone(form.cleaned_data["number"])

        context = {
            **self.admin_site.each_context(request),
            "title": _("Telegram number check"),
            "form": form,
            "result": result,
            "opts": self.model._meta,
            "cl": {"opts": self.model._meta},
        }
        if extra_context:
            context.update(extra_context)

        return TemplateResponse(
            request,
            "admin/crm/telegramnumbercheck/change_list.html",
            context,
        )


@admin.register(FinancialAccount)
class FinancialAccountAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "bank_name", "iban", "currency"]
    search_fields = ["name", "bank_name", "iban"]


@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "account",
        "amount",
        "kind",
        "income_type",
        "expense_type",
        "matched_transaction",
        "crm_orders_display",
    ]
    list_filter = ["kind", "income_type", "expense_type", "account"]
    date_hierarchy = "date"
    search_fields = ["description", "counterparty_name", "external_id"]
    autocomplete_fields = ["account", "crm_orders", "matched_transaction"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("matched_transaction__account")
            .prefetch_related("crm_orders")
        )

    @admin.display(description=_("CRM orders"))
    def crm_orders_display(self, obj: FinancialTransaction) -> str:
        return ", ".join(str(order) for order in obj.crm_orders.all())
    change_list_template = "admin/crm/financialtransaction/change_list.html"

    def get_urls(self):
        urls = [
            path(
                "upload-bog/",
                self.admin_site.admin_view(self.upload_bog_view),
                name="crm_financialtransaction_upload_bog",
            ),
            path(
                "upload-liberty/",
                self.admin_site.admin_view(self.upload_liberty_view),
                name="crm_financialtransaction_upload_liberty",
            ),
            path(
                "upload-flowwow/",
                self.admin_site.admin_view(self.upload_flowwow_view),
                name="crm_financialtransaction_upload_flowwow",
            ),
        ]
        return urls + super().get_urls()

    def upload_bog_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        if request.method == "POST":
            form = BogStatementUploadForm(request.POST, request.FILES)
            if form.is_valid():
                result = import_bog_statement(form.cleaned_data["file"])
                if result.error:
                    self.message_user(request, result.error, level=messages.ERROR)
                else:
                    self.message_user(
                        request,
                        _("Imported %(created)s, skipped %(skipped)s duplicates.")
                        % {"created": result.created, "skipped": result.skipped},
                    )
                    return redirect("admin:crm_financialtransaction_changelist")
        else:
            form = BogStatementUploadForm()
        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "opts": self.model._meta,
            "title": _("Upload Bank of Georgia statement"),
        }
        return TemplateResponse(
            request,
            "admin/crm/financialtransaction/upload_bog.html",
            context,
        )

    def upload_liberty_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        if request.method == "POST":
            form = BogStatementUploadForm(request.POST, request.FILES)
            if form.is_valid():
                result = import_liberty_statement(form.cleaned_data["file"])
                if result.error:
                    self.message_user(request, result.error, level=messages.ERROR)
                else:
                    self.message_user(
                        request,
                        _("Imported %(created)s, skipped %(skipped)s duplicates.")
                        % {"created": result.created, "skipped": result.skipped},
                    )
                    return redirect("admin:crm_financialtransaction_changelist")
        else:
            form = BogStatementUploadForm()
        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "opts": self.model._meta,
            "title": _("Upload Liberty statement"),
        }
        return TemplateResponse(
            request,
            "admin/crm/financialtransaction/upload_bog.html",
            context,
        )

    def upload_flowwow_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        if request.method == "POST":
            form = BogStatementUploadForm(request.POST, request.FILES)
            if form.is_valid():
                result = import_flowwow_statement(form.cleaned_data["file"])
                if result.error:
                    self.message_user(request, result.error, level=messages.ERROR)
                else:
                    self.message_user(
                        request,
                        _("Imported %(created)s, skipped %(skipped)s duplicates.")
                        % {"created": result.created, "skipped": result.skipped},
                    )
                    return redirect("admin:crm_financialtransaction_changelist")
        else:
            form = BogStatementUploadForm()
        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "opts": self.model._meta,
            "title": _("Upload Flowwow statement"),
        }
        return TemplateResponse(
            request,
            "admin/crm/financialtransaction/upload_bog.html",
            context,
        )
