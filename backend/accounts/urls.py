from django.urls import path

from accounts.views import (
    CsrfView,
    EmployeeDetailView,
    EmployeeListView,
    GroupDetailView,
    GroupListView,
    LoginView,
    LogoutView,
    MeView,
    PermissionListView,
)

urlpatterns = [
    path("auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("accounts/employees/", EmployeeListView.as_view(), name="employees"),
    path("accounts/employees/<int:pk>/", EmployeeDetailView.as_view(), name="employee-detail"),
    path("accounts/permissions/", PermissionListView.as_view(), name="section-permissions"),
    path("accounts/groups/", GroupListView.as_view(), name="access-groups"),
    path("accounts/groups/<int:pk>/", GroupDetailView.as_view(), name="access-group-detail"),
]
