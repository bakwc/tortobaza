from decimal import Decimal
from pathlib import Path

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import FinancialTransaction
from crm.views import IsFinanceAdmin
from inventory.models import (
    InventoryCount,
    Production,
    StockMovement,
    Supplier,
    Supply,
    SupplyReceipt,
    WriteOff,
    WriteOffReason,
)
from inventory.receipts import recognize_receipt, to_jpeg
from inventory.serializers import (
    FinancialTransactionQuerySerializer,
    InventoryCountSerializer,
    MovementQuerySerializer,
    ProductionSerializer,
    StockQuerySerializer,
    SupplierSerializer,
    SupplyReceiptSerializer,
    SupplySerializer,
    WriteOffReasonSerializer,
    WriteOffSerializer,
    movement_payloads,
    show_costs,
    transaction_payload,
)
from inventory.services import (
    apply_production,
    apply_supply,
    apply_write_off,
    close_inventory_count,
    delete_document,
    stock_levels,
    stock_of,
)
from menu.models import Ingredient, SemiProduct
from menu.views import delete_unless_protected, serializer_context


class InventoryListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def get_queryset(self):
        raise NotImplementedError

    def apply(self, instance) -> None:
        return None

    def get(self, request):
        serializer = self.serializer_class(
            self.get_queryset(),
            many=True,
            context=serializer_context(request),
        )
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request):
        context = serializer_context(request)
        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        self.apply(instance)
        return Response(
            self.serializer_class(instance, context=context).data,
            status=status.HTTP_201_CREATED,
        )


class InventoryDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def get_queryset(self):
        raise NotImplementedError

    def apply(self, instance) -> None:
        return None

    def remove(self, instance) -> Response:
        delete_document(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get(self, request, pk: int):
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(self.serializer_class(instance, context=serializer_context(request)).data)

    @transaction.atomic
    def put(self, request, pk: int):
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        context = serializer_context(request)
        serializer = self.serializer_class(instance, data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        self.apply(instance)
        return Response(self.serializer_class(instance, context=context).data)

    @transaction.atomic
    def delete(self, request, pk: int):
        return self.remove(get_object_or_404(self.get_queryset(), pk=pk))


class SupplierListView(InventoryListView):
    permission_classes = [IsAuthenticated, IsFinanceAdmin]
    serializer_class = SupplierSerializer

    def get_queryset(self):
        return Supplier.objects.all()


class SupplierDetailView(InventoryDetailView):
    permission_classes = [IsAuthenticated, IsFinanceAdmin]
    serializer_class = SupplierSerializer

    def get_queryset(self):
        return Supplier.objects.all()

    def remove(self, instance) -> Response:
        return delete_unless_protected(instance)


class WriteOffReasonListView(InventoryListView):
    serializer_class = WriteOffReasonSerializer

    def get_queryset(self):
        return WriteOffReason.objects.all()


class WriteOffReasonDetailView(InventoryDetailView):
    serializer_class = WriteOffReasonSerializer

    def get_queryset(self):
        return WriteOffReason.objects.all()

    def remove(self, instance) -> Response:
        return delete_unless_protected(instance)


def supplies_queryset():
    return Supply.objects.select_related("supplier", "financial_transaction__account").prefetch_related("receipts")


RECEIPT_EXTENSIONS = {"jpg", "jpeg", "png", "heic"}


class SupplyReceiptUploadView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]
    parser_classes = [MultiPartParser]

    @transaction.atomic
    def post(self, request):
        upload = request.FILES["image"]
        extension = Path(upload.name).suffix.lower().lstrip(".")
        if extension not in RECEIPT_EXTENSIONS:
            raise ValidationError({"image": "Upload a jpg, png, or heic image."})
        jpeg = to_jpeg(upload)
        recognized = recognize_receipt(jpeg.read())
        jpeg.seek(0)
        supplier = Supplier.objects.filter(name__iexact=recognized["merchant_name"]).first()
        recognized["supplier"] = None if supplier is None else supplier.pk
        receipt = SupplyReceipt.objects.create(image=jpeg, recognized=recognized)
        return Response(SupplyReceiptSerializer(receipt).data, status=status.HTTP_201_CREATED)


class SupplyListView(InventoryListView):
    permission_classes = [IsAuthenticated, IsFinanceAdmin]
    serializer_class = SupplySerializer

    def get_queryset(self):
        return supplies_queryset()

    def apply(self, instance) -> None:
        apply_supply(instance)


class SupplyDetailView(InventoryDetailView):
    permission_classes = [IsAuthenticated, IsFinanceAdmin]
    serializer_class = SupplySerializer

    def get_queryset(self):
        return supplies_queryset()

    def apply(self, instance) -> None:
        apply_supply(instance)


class ProductionListView(InventoryListView):
    serializer_class = ProductionSerializer

    def get_queryset(self):
        return Production.objects.select_related("semi_product", "created_by")

    def apply(self, instance) -> None:
        apply_production(instance)


class ProductionDetailView(InventoryDetailView):
    serializer_class = ProductionSerializer

    def get_queryset(self):
        return Production.objects.select_related("semi_product", "created_by")

    def apply(self, instance) -> None:
        apply_production(instance)


class WriteOffListView(InventoryListView):
    serializer_class = WriteOffSerializer

    def get_queryset(self):
        return WriteOff.objects.select_related("reason", "created_by")

    def apply(self, instance) -> None:
        apply_write_off(instance)


class WriteOffDetailView(InventoryDetailView):
    serializer_class = WriteOffSerializer

    def get_queryset(self):
        return WriteOff.objects.select_related("reason", "created_by")

    def apply(self, instance) -> None:
        apply_write_off(instance)


class InventoryCountListView(InventoryListView):
    serializer_class = InventoryCountSerializer

    def get_queryset(self):
        return InventoryCount.objects.select_related("created_by")


class InventoryCountDetailView(InventoryDetailView):
    serializer_class = InventoryCountSerializer

    def get_queryset(self):
        return InventoryCount.objects.select_related("created_by")


class InventoryCountCloseView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        count = get_object_or_404(InventoryCount, pk=pk)
        if count.status == InventoryCount.STATUS_CLOSED:
            return Response(
                {"detail": "Inventory count is already closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        close_inventory_count(count)
        context = serializer_context(request)
        return Response(InventoryCountSerializer(count, context=context).data)


class StockView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = StockQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        levels = stock_levels(query.validated_data.get("date"), None)
        context = serializer_context(request)
        rows = []
        components = [
            *Ingredient.objects.select_related("category"),
            *SemiProduct.objects.filter(is_produced=True),
        ]
        for component in components:
            quantity = stock_of(component, levels)
            is_ingredient = isinstance(component, Ingredient)
            row = {
                "ingredient": component.pk if is_ingredient else None,
                "semi_product": None if is_ingredient else component.pk,
                "name": component.name,
                "unit": component.unit,
                "category_name": (
                    component.category.name if is_ingredient and component.category_id is not None else None
                ),
                "is_active": component.is_active,
                "quantity": str(quantity),
            }
            if show_costs(context):
                row["avg_cost"] = str(component.avg_cost)
                row["value"] = str((quantity * component.avg_cost).quantize(Decimal("0.01")))
            rows.append(row)
        return Response(rows)


class MovementListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = MovementQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        movements = StockMovement.objects.filter(**query.validated_data).order_by("-date", "-id")
        return Response(movement_payloads(movements, serializer_context(request)))


class SupplyTransactionListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def get(self, request):
        query = FinancialTransactionQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        free = Q(supply__isnull=True)
        if "supply" in query.validated_data:
            free = free | Q(supply__pk=query.validated_data["supply"])
        transactions = (
            FinancialTransaction.objects.filter(
                kind=FinancialTransaction.KIND_EXPENSE,
                expense_type=FinancialTransaction.EXPENSE_PRODUCTS,
            )
            .filter(free)
            .select_related("account")
            .order_by("-date", "-id")[:200]
        )
        return Response([transaction_payload(row) for row in transactions])
