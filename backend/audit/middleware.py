from audit.context import bind, release


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user if request.user.is_authenticated else None
        tokens = bind(user)
        try:
            return self.get_response(request)
        finally:
            release(tokens)
