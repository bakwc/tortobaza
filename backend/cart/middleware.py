import uuid

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject

from cart.models import Cart


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


def _get_token_from_request(request) -> uuid.UUID | None:
    cookie_name = getattr(settings, "CART_TOKEN_COOKIE_NAME", "cart_token")
    header_name = getattr(settings, "CART_TOKEN_HEADER", "HTTP_X_CART_TOKEN")
    token = _parse_uuid(request.COOKIES.get(cookie_name))
    if token is not None:
        return token
    return _parse_uuid(request.META.get(header_name))


def _resolve_cart(request) -> Cart | None:
    token = _get_token_from_request(request)
    if token is None:
        return None
    return Cart.objects.filter(token=token, is_ordered=False).first()


class CartTokenMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.cart_token = _get_token_from_request(request)
        request.cart = SimpleLazyObject(lambda: _resolve_cart(request))

    def process_response(self, request, response):
        new_token = getattr(response, "_set_cart_token", None)
        if new_token is not None:
            cookie_name = getattr(settings, "CART_TOKEN_COOKIE_NAME", "cart_token")
            max_age = getattr(settings, "CART_TOKEN_COOKIE_MAX_AGE", 60 * 60 * 24 * 30)
            response.set_cookie(
                cookie_name,
                str(new_token),
                max_age=max_age,
                httponly=True,
                samesite="Lax",
            )
        return response


def get_or_create_cart(request) -> Cart:
    cart = request.cart
    if cart is not None:
        return cart
    cart = Cart.objects.create()
    request.cart = cart
    request.cart_token = cart.token
    request._new_cart_token = cart.token
    return cart
