from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from accounts.models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = _("Profile")


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = BaseUserAdmin.list_display + (
        "get_hourly_rate",
        "get_monthly_rate",
        "get_can_login",
        "get_is_finance_admin",
        "get_is_active_courier",
    )

    @admin.display(description=_("Hourly rate"))
    def get_hourly_rate(self, obj):
        profile = getattr(obj, "profile", None)
        if profile is None:
            return None
        return profile.hourly_rate

    @admin.display(description=_("Monthly rate"))
    def get_monthly_rate(self, obj):
        profile = getattr(obj, "profile", None)
        if profile is None:
            return None
        return profile.monthly_rate

    @admin.display(description=_("Can log in"), boolean=True)
    def get_can_login(self, obj):
        profile = UserProfile.objects.filter(user=obj).first()
        if profile is None:
            return True
        return profile.can_login

    @admin.display(description=_("Finance admin"), boolean=True)
    def get_is_finance_admin(self, obj):
        profile = UserProfile.objects.filter(user=obj).first()
        if profile is None:
            return False
        return profile.is_finance_admin

    @admin.display(description=_("Active courier"), boolean=True)
    def get_is_active_courier(self, obj):
        profile = UserProfile.objects.filter(user=obj).first()
        if profile is None:
            return False
        return profile.is_active_courier


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
