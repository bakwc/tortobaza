from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.middleware import get_or_create_cart
from cart.models import CartItem, CartItemOption
from cart.serializers import (
    CartItemCreateSerializer,
    CartItemReadSerializer,
    CartItemUpdateSerializer,
    CartReadSerializer,
)


def _serialize_cart(cart, request) -> dict:
    return CartReadSerializer(cart, context={"request": request}).data


def _attach_token_cookie(response, request) -> None:
    new_token = getattr(request, "_new_cart_token", None)
    if new_token is not None:
        response._set_cart_token = new_token


class CartView(APIView):
    def get(self, request):
        cart = get_or_create_cart(request)
        response = Response(_serialize_cart(cart, request))
        _attach_token_cookie(response, request)
        return response

    def delete(self, request):
        cart = request.cart
        if cart is not None:
            cart.items.all().delete()
            cart.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemListView(APIView):
    def post(self, request):
        cart = get_or_create_cart(request)
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            item = CartItem.objects.create(
                cart=cart,
                product=data["product"],
                quantity=data["quantity"],
                comment=data.get("comment", ""),
            )
            CartItemOption.objects.bulk_create(
                [CartItemOption(cart_item=item, option=option) for option in data["options"]]
            )
            cart.save()

        item.refresh_from_db()
        item = (
            CartItem.objects
            .select_related("product")
            .prefetch_related("options__option__group", "product__images")
            .get(pk=item.pk)
        )
        response = Response(
            CartItemReadSerializer(item, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
        _attach_token_cookie(response, request)
        return response


class CartItemDetailView(APIView):
    def _get_item(self, request, item_id: int) -> CartItem:
        cart = request.cart
        if cart is None:
            return get_object_or_404(CartItem, pk=item_id, cart_id=-1)
        return get_object_or_404(CartItem, pk=item_id, cart=cart)

    def patch(self, request, item_id: int):
        item = self._get_item(request, item_id)
        serializer = CartItemUpdateSerializer(data=request.data, context={"cart_item": item})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            if "quantity" in data:
                item.quantity = data["quantity"]
            if "comment" in data:
                item.comment = data["comment"]
            item.save()
            if "options" in data:
                item.options.all().delete()
                CartItemOption.objects.bulk_create(
                    [CartItemOption(cart_item=item, option=option) for option in data["options"]]
                )
            item.cart.save()

        item = (
            CartItem.objects
            .select_related("product")
            .prefetch_related("options__option__group", "product__images")
            .get(pk=item.pk)
        )
        return Response(CartItemReadSerializer(item, context={"request": request}).data)

    def delete(self, request, item_id: int):
        item = self._get_item(request, item_id)
        cart = item.cart
        item.delete()
        cart.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
