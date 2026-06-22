from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget
from django.contrib.auth.models import User
from django.template.response import TemplateResponse

from attendance.models import AttendanceEvent, SalaryCalculation
from attendance.salary import compute_salary


class SalaryCalculationForm(forms.Form):
    employee = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("username"),
    )
    start_date = forms.DateField(widget=AdminDateWidget())
    end_date = forms.DateField(widget=AdminDateWidget())


@admin.register(AttendanceEvent)
class AttendanceEventAdmin(admin.ModelAdmin):
    list_display = ["user", "event_type", "timestamp"]
    list_filter = ["event_type", "user"]
    date_hierarchy = "timestamp"
    search_fields = ["user__username"]


@admin.register(SalaryCalculation)
class SalaryCalculationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        form = SalaryCalculationForm(request.GET or None)
        result = None
        if form.is_valid():
            result = compute_salary(
                form.cleaned_data["employee"],
                form.cleaned_data["start_date"],
                form.cleaned_data["end_date"],
            )

        context = {
            **self.admin_site.each_context(request),
            "title": "Salary calculation",
            "form": form,
            "result": result,
            "opts": self.model._meta,
            "cl": {"opts": self.model._meta},
        }
        if extra_context:
            context.update(extra_context)

        return TemplateResponse(
            request,
            "admin/attendance/salarycalculation/change_list.html",
            context,
        )
