from django.utils import translation


class AdminRussianMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/"):
            with translation.override("ru"):
                return self.get_response(request)
        return self.get_response(request)
