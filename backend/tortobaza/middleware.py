from django.contrib.auth import logout
from django.utils import translation

from accounts.models import UserProfile


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
