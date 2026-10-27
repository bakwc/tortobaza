from django.contrib.auth import logout
from django.http import JsonResponse
from django.utils import translation

from accounts.models import UserProfile
from tortobaza.finance_db import use_finance_db

_FINANCE_API_PREFIXES = (
    "/api/crm/finance/accounts/",
    "/api/crm/finance/transactions/",
)
_FINANCE_SCOPES = {
    "business": "default",
    "personal": "personal",
}


class CanLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            profile = UserProfile.objects.filter(user=user).first()
            if profile is not None and not profile.can_login:
                logout(request)
        return self.get_response(request)


class AdminRussianMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/"):
            with translation.override("ru"):
                return self.get_response(request)
        return self.get_response(request)


class FinanceScopeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/personal-admin/"):
            with use_finance_db("personal"):
                return self.get_response(request)
        if request.path.startswith(_FINANCE_API_PREFIXES):
            alias = _FINANCE_SCOPES.get(request.GET.get("scope"))
            if alias is None:
                return JsonResponse({"detail": "Invalid scope."}, status=400)
            with use_finance_db(alias):
                return self.get_response(request)
        return self.get_response(request)
