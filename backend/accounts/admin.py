from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from accounts.models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "profile"


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = BaseUserAdmin.list_display + ("get_hourly_rate",)

    @admin.display(description="hourly rate")
    def get_hourly_rate(self, obj):
        profile = getattr(obj, "profile", None)
        if profile is None:
            return None
        return profile.hourly_rate


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
