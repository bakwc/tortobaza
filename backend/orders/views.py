from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order, PickupLocation
from orders.schedule import build_fulfillment_options
from orders.serializers import (
    OrderCreateInputSerializer,
    OrderPreviewInputSerializer,
    OrderReadSerializer,
    PickupLocationSerializer,
    PromoValidateInputSerializer,
)
from orders.services import (
    compute_totals,
    create_order_from_cart,
    get_promo_by_code,
)


class PickupLocationListView(generics.ListAPIView):
    serializer_class = PickupLocationSerializer
    pagination_class = None

    def get_queryset(self):
        return PickupLocation.objects.filter(is_active=True)


class FulfillmentOptionsView(APIView):
    def get(self, request):
        ftype = request.query_params.get("type")
        if ftype not in ("delivery", "pickup"):
            return Response(
                {"detail": "Query parameter type must be delivery or pickup."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cart = request.cart
        if cart is None or not cart.items.exists():
            return Response(
                {"detail": "Cart is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = build_fulfillment_options(cart)
        return Response(data)


class PromoCodeValidateView(APIView):
    def post(self, request):
        cart = request.cart
        if cart is None or not cart.items.exists():
            return Response(
                {"valid": False, "detail": "Cart is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = PromoValidateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        promo = get_promo_by_code(serializer.validated_data["code"])
        totals = compute_totals(cart, promo)
        return Response(
            {
                "valid": True,
                "code": promo.code,
                "discount_type": promo.discount_type,
                "discount_value": promo.discount_value,
                "subtotal": totals["subtotal"],
                "discount_total": totals["discount_total"],
                "total": totals["total"],
            }
        )


class OrderPreviewView(APIView):
    def post(self, request):
        cart = request.cart
        if cart is None or not cart.items.exists():
            return Response(
                {"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST
            )
        serializer = OrderPreviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        promo = None
        promo_code = data.get("promo_code") or ""
        if promo_code:
            promo = get_promo_by_code(promo_code)

        totals = compute_totals(cart, promo)
        return Response(
            {
                "fulfillment_type": data["fulfillment_type"],
                "subtotal": totals["subtotal"],
                "discount_total": totals["discount_total"],
                "total": totals["total"],
                "promo_code": promo.code if promo else None,
            }
        )


class OrderCreateView(APIView):
    def post(self, request):
        cart = request.cart
        if cart is None or not cart.items.exists():
            return Response(
                {"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = OrderCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = create_order_from_cart(cart, serializer.validated_data)

        order = (
            Order.objects
            .select_related("pickup_location", "delivery_address")
            .prefetch_related("items__options")
            .get(pk=order.pk)
        )
        return Response(
            OrderReadSerializer(order).data, status=status.HTTP_201_CREATED
        )


class OrderDetailView(APIView):
    def get(self, request, number: str):
        token = request.query_params.get("token")
        if not token:
            return Response(
                {"detail": "Lookup token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order = get_object_or_404(Order, number=number, lookup_token=token)
        return Response(OrderReadSerializer(order).data)
