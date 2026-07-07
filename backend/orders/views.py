import uuid

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.liberty import (
    build_callback_check,
    build_start_fields,
    callback_response_xml,
    order_amount_tetri,
)
from orders.models import LibertyPayment, Order, PickupLocation
from orders.schedule import build_fulfillment_options
from orders.serializers import (
    LibertyPaymentStartInputSerializer,
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
                {"detail": _("Query parameter type must be delivery or pickup.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cart = request.cart
        if cart is None or not cart.items.exists():
            return Response(
                {"detail": _("Cart is empty.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = build_fulfillment_options(cart)
        return Response(data)


class PromoCodeValidateView(APIView):
    def post(self, request):
        cart = request.cart
        if cart is None or not cart.items.exists():
            return Response(
                {"valid": False, "detail": _("Cart is empty.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = PromoValidateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        promo = get_promo_by_code(serializer.validated_data["code"])
        totals = compute_totals(cart, promo, Order.FULFILLMENT_PICKUP)
        return Response(
            {
                "valid": True,
                "code": promo.code,
                "discount_type": promo.discount_type,
                "discount_value": str(promo.discount_value),
                "subtotal": str(totals["subtotal"]),
                "discount_total": str(totals["discount_total"]),
                "delivery_fee": str(totals["delivery_fee"]),
                "total": str(totals["total"]),
            }
        )


class OrderPreviewView(APIView):
    def post(self, request):
        cart = request.cart
        if cart is None or not cart.items.exists():
            return Response(
                {"detail": _("Cart is empty.")}, status=status.HTTP_400_BAD_REQUEST
            )
        serializer = OrderPreviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        promo = None
        promo_code = data.get("promo_code") or ""
        if promo_code:
            promo = get_promo_by_code(promo_code)

        totals = compute_totals(cart, promo, data["fulfillment_type"])
        return Response(
            {
                "fulfillment_type": data["fulfillment_type"],
                "subtotal": str(totals["subtotal"]),
                "discount_total": str(totals["discount_total"]),
                "delivery_fee": str(totals["delivery_fee"]),
                "total": str(totals["total"]),
                "promo_code": promo.code if promo else None,
            }
        )


class OrderCreateView(APIView):
    def post(self, request):
        cart = request.cart
        if cart is None or not cart.items.exists():
            return Response(
                {"detail": _("Cart is empty.")}, status=status.HTTP_400_BAD_REQUEST
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
                {"detail": _("Lookup token is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order = get_object_or_404(Order, number=number, lookup_token=token)
        return Response(OrderReadSerializer(order).data)


class LibertyPaymentStartView(APIView):
    def post(self, request):
        serializer = LibertyPaymentStartInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        order = get_object_or_404(Order, number=data["number"], lookup_token=data["token"])
        if order.payment_method != Order.PAYMENT_CARD:
            return Response(
                {"detail": _("This order does not use card payment.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if order.payment_status == Order.PAYMENT_PAID:
            return Response(
                {"detail": _("This order is already paid.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        testmode = settings.LIBERTY_PAY_TESTMODE == "1"
        payment = LibertyPayment.objects.create(
            order=order,
            ordercode=f"{order.number}-{uuid.uuid4().hex[:12]}",
            amount_tetri=order_amount_tetri(order),
            testmode=testmode,
        )
        fields = build_start_fields(payment, order)
        return Response(
            {
                "action_url": settings.LIBERTY_PAY_URL,
                "fields": fields,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class LibertyCallbackView(APIView):
    def post(self, request):
        params = request.POST
        status_value = params.get("status", "")
        transactioncode = params.get("transactioncode", "") or params.get("transaction code", "")
        amount = params.get("amount", "")
        currency = params.get("currency", "")
        ordercode = params.get("ordercode", "")
        paymethod = params.get("paymethod", "")
        customdata_value = params.get("customdata", "")
        testmode = params.get("testmode", "")
        check = params.get("check", "")

        expected_check = build_callback_check(
            status_value,
            transactioncode,
            amount,
            currency,
            ordercode,
            paymethod,
            customdata_value,
            testmode,
            settings.LIBERTY_PAY_SECRET,
        )
        if check != expected_check:
            xml = callback_response_xml("-3", "Invalid signature", transactioncode)
            return HttpResponse(xml, content_type="text/xml")

        payment = LibertyPayment.objects.filter(ordercode=ordercode).select_related("order").first()
        if payment is None:
            xml = callback_response_xml("-2", "Transaction not found", transactioncode)
            return HttpResponse(xml, content_type="text/xml")

        if str(payment.amount_tetri) != amount:
            xml = callback_response_xml("-3", "Amount mismatch", transactioncode)
            return HttpResponse(xml, content_type="text/xml")

        if payment.status == LibertyPayment.STATUS_COMPLETED:
            xml = callback_response_xml("1", "Duplicate", transactioncode)
            return HttpResponse(xml, content_type="text/xml")

        payment.pay_method = paymethod
        payment.raw_callback = request.body.decode("utf-8", errors="replace")

        if status_value == "COMPLETED":
            payment.status = LibertyPayment.STATUS_COMPLETED
            payment.transaction_code = transactioncode
            payment.save()
            Order.objects.filter(pk=payment.order_id).update(payment_status=Order.PAYMENT_PAID)
            xml = callback_response_xml("0", "Ok", transactioncode)
            return HttpResponse(xml, content_type="text/xml")

        if status_value == "CANCELED":
            payment.status = LibertyPayment.STATUS_CANCELED
        else:
            payment.status = LibertyPayment.STATUS_ERROR
        payment.save()
        xml = callback_response_xml("0", "Ok", transactioncode)
        return HttpResponse(xml, content_type="text/xml")
