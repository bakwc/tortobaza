from django.contrib.admin.utils import NestedObjects
from django.db import router, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import SectionPermission
from cart.models import CartItem
from catalog.auto_translate import schedule_translation, translate_now
from catalog.models import (
    Category,
    CategoryLanding,
    Option,
    OptionGroup,
    Product,
    ProductImage,
)
from catalog.site_serializers import (
    SiteCategoryLandingSerializer,
    SiteCategorySerializer,
    SiteImageUploadSerializer,
    SiteOptionGroupSerializer,
    SiteProductImagePatchSerializer,
    SiteProductImageReorderSerializer,
    SiteProductImageSerializer,
    SiteProductImageUploadSerializer,
    SiteProductListSerializer,
    SiteProductSerializer,
    SiteTechCardChoiceSerializer,
    SiteTranslationRequestSerializer,
)
from menu.models import TechCard


def serializer_context(request) -> dict:
    return {"request": request}


def protected_objects(instance) -> list[str]:
    collector = NestedObjects(using=router.db_for_write(type(instance)))
    collector.collect([instance])
    return sorted({str(obj) for obj in collector.protected})


def product_delete_blockers(product: Product) -> tuple[list[CartItem], list[str]]:
    collector = NestedObjects(using=router.db_for_write(Product))
    collector.collect([product])
    cart_items = list(CartItem.objects.filter(product=product).order_by("id"))
    cart_item_ids = {item.pk for item in cart_items}
    extra = sorted(
        {
            str(obj)
            for obj in collector.protected
            if not isinstance(obj, CartItem) or obj.pk not in cart_item_ids
        }
    )
    return cart_items, extra


def delete_unless_protected(instance) -> Response:
    protected = protected_objects(instance)
    if protected:
        return Response(
            {"detail": "Object is in use.", "protected": protected},
            status=status.HTTP_400_BAD_REQUEST,
        )
    instance.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


class SiteListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("catalog")]
    serializer_class = None

    def get_queryset(self):
        raise NotImplementedError

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
        return Response(
            self.serializer_class(instance, context=context).data,
            status=status.HTTP_201_CREATED,
        )


class SiteDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("catalog")]
    serializer_class = None

    def get_queryset(self):
        raise NotImplementedError

    def get(self, request, pk: int):
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(
            self.serializer_class(instance, context=serializer_context(request)).data
        )

    @transaction.atomic
    def put(self, request, pk: int):
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        context = serializer_context(request)
        serializer = self.serializer_class(instance, data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance, context=context).data)

    @transaction.atomic
    def delete(self, request, pk: int):
        return delete_unless_protected(get_object_or_404(self.get_queryset(), pk=pk))


class SiteCategoryListView(SiteListView):
    serializer_class = SiteCategorySerializer

    def get_queryset(self):
        return Category.objects.all()


class SiteCategoryDetailView(SiteDetailView):
    serializer_class = SiteCategorySerializer

    def get_queryset(self):
        return Category.objects.all()


class SiteCategoryImageView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("catalog")]

    def post(self, request, pk: int):
        category = get_object_or_404(Category, pk=pk)
        serializer = SiteImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if category.image:
            category.image.delete(save=False)
        category.image = serializer.validated_data["image"]
        category.save(update_fields=["image", "updated_at"])
        return Response(
            SiteCategorySerializer(category, context=serializer_context(request)).data
        )

    def delete(self, request, pk: int):
        category = get_object_or_404(Category, pk=pk)
        if category.image:
            category.image.delete(save=False)
            category.image = ""
            category.save(update_fields=["image", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SiteCategoryLandingListView(SiteListView):
    serializer_class = SiteCategoryLandingSerializer

    def get_queryset(self):
        return CategoryLanding.objects.select_related("source")


class SiteCategoryLandingDetailView(SiteDetailView):
    serializer_class = SiteCategoryLandingSerializer

    def get_queryset(self):
        return CategoryLanding.objects.select_related("source")


class SiteCategoryLandingImageView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("catalog")]

    def post(self, request, pk: int):
        landing = get_object_or_404(CategoryLanding, pk=pk)
        serializer = SiteImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if landing.image:
            landing.image.delete(save=False)
        landing.image = serializer.validated_data["image"]
        landing.save(update_fields=["image", "updated_at"])
        return Response(
            SiteCategoryLandingSerializer(landing, context=serializer_context(request)).data
        )

    def delete(self, request, pk: int):
        landing = get_object_or_404(CategoryLanding, pk=pk)
        if landing.image:
            landing.image.delete(save=False)
            landing.image = ""
            landing.save(update_fields=["image", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SiteOptionGroupListView(SiteListView):
    serializer_class = SiteOptionGroupSerializer

    def get_queryset(self):
        return OptionGroup.objects.prefetch_related("options")


class SiteOptionGroupDetailView(SiteDetailView):
    serializer_class = SiteOptionGroupSerializer

    def get_queryset(self):
        return OptionGroup.objects.prefetch_related("options")


class SiteOptionImageView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("catalog")]

    def post(self, request, pk: int):
        option = get_object_or_404(Option, pk=pk)
        serializer = SiteImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if option.image:
            option.image.delete(save=False)
        option.image = serializer.validated_data["image"]
        option.save(update_fields=["image"])
        group = option.group
        return Response(
            SiteOptionGroupSerializer(group, context=serializer_context(request)).data
        )

    def delete(self, request, pk: int):
        option = get_object_or_404(Option, pk=pk)
        if option.image:
            option.image.delete(save=False)
            option.image = ""
            option.save(update_fields=["image"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SiteProductListView(SiteListView):
    serializer_class = SiteProductListSerializer

    @transaction.atomic
    def post(self, request):
        context = serializer_context(request)
        serializer = SiteProductSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            SiteProductSerializer(instance, context=context).data,
            status=status.HTTP_201_CREATED,
        )

    def get_queryset(self):
        qs = Product.objects.select_related("category").prefetch_related("images")
        category = self.request.GET.get("category")
        search = self.request.GET.get("search")
        if category:
            if category.isdigit():
                qs = qs.filter(category_id=int(category))
            else:
                qs = qs.filter(category__slug=category)
        if search:
            term = search.strip()
            if term:
                qs = qs.filter(
                    Q(name_en__icontains=term)
                    | Q(name_ka__icontains=term)
                    | Q(name_ru__icontains=term)
                    | Q(slug__icontains=term)
                )
        return qs.order_by("category__position", "category__name", "position", "-created_at")


class SiteProductDetailView(SiteDetailView):
    serializer_class = SiteProductSerializer

    def get_queryset(self):
        return Product.objects.select_related("category", "tech_card").prefetch_related(
            "images", "product_option_groups__option_group"
        )

    @transaction.atomic
    def delete(self, request, pk: int):
        product = get_object_or_404(self.get_queryset(), pk=pk)
        cart_items, extra = product_delete_blockers(product)
        if extra:
            return Response(
                {"detail": "Object is in use.", "protected": extra},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.query_params.get("confirm") != "1":
            return Response(
                {
                    "related": [
                        {"label": f"{product.name} × {item.quantity}"} for item in cart_items[:8]
                    ],
                    "related_total": len(cart_items),
                },
                status=status.HTTP_409_CONFLICT,
            )
        if cart_items:
            CartItem.objects.filter(pk__in=[item.pk for item in cart_items]).delete()
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SiteProductImageCreateView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("catalog")]

    def post(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)
        serializer = SiteProductImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        position = product.images.count()
        row = ProductImage.objects.create(
            product=product,
            image=data["image"],
            position=position,
            alt_en=data.get("alt_en") or "",
            alt_ka=data.get("alt_ka") or "",
            alt_ru=data.get("alt_ru") or "",
            crop_left=data.get("crop_left"),
            crop_top=data.get("crop_top"),
            crop_size=data.get("crop_size"),
        )
        schedule_translation([row])
        return Response(
            SiteProductImageSerializer(row, context=serializer_context(request)).data,
            status=status.HTTP_201_CREATED,
        )


class SiteProductImageDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("catalog")]

    def patch(self, request, pk: int, image_pk: int):
        row = get_object_or_404(ProductImage, pk=image_pk, product_id=pk)
        serializer = SiteProductImagePatchSerializer(row, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        row = serializer.save()
        return Response(
            SiteProductImageSerializer(row, context=serializer_context(request)).data
        )

    def delete(self, request, pk: int, image_pk: int):
        row = get_object_or_404(ProductImage, pk=image_pk, product_id=pk)
        row.image.delete(save=False)
        row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SiteProductImageReorderView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("catalog")]

    @transaction.atomic
    def post(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)
        serializer = SiteProductImageReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]
        images = list(product.images.filter(pk__in=ids))
        if len(images) != len(ids):
            return Response({"detail": "Unknown image id."}, status=status.HTTP_400_BAD_REQUEST)
        by_id = {row.pk: row for row in images}
        for position, image_id in enumerate(ids):
            row = by_id[image_id]
            row.position = position
            row.save(update_fields=["position"])
        rows = product.images.order_by("position", "id")
        return Response(
            SiteProductImageSerializer(rows, many=True, context=serializer_context(request)).data
        )


class SiteTranslationView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("catalog")]

    def post(self, request):
        serializer = SiteTranslationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response({"items": translate_now(data["language"], data["items"])})


class SiteTechCardChoicesView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("catalog")]

    def get(self, request):
        rows = TechCard.objects.filter(is_active=True).order_by("name")
        return Response(
            SiteTechCardChoiceSerializer(rows, many=True, context=serializer_context(request)).data
        )
