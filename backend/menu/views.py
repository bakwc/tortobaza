from django.contrib.admin.utils import NestedObjects
from django.db import router, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import HasPerm, SectionPermission, can_see_costs
from catalog.models import Option
from menu.models import (
    Ingredient,
    IngredientCategory,
    Modifier,
    ModifierGroup,
    SemiProduct,
    SemiProductCategory,
    SemiProductImage,
    TechCard,
    TechCardCategory,
    TechCardImage,
)
from menu.recipes import missing_modifier_compositions, tech_card_cost
from menu.serializers import (
    CatalogOptionSerializer,
    AssignIngredientCategorySerializer,
    AssignSemiProductCategorySerializer,
    AssignTechCardCategorySerializer,
    IngredientCategorySerializer,
    IngredientSerializer,
    MissingModifierLineSerializer,
    MenuImageUploadSerializer,
    ModifierGroupSerializer,
    SemiProductCategorySerializer,
    SemiProductSerializer,
    menu_image_rows,
    TechCardCategorySerializer,
    TechCardCostQuerySerializer,
    TechCardSerializer,
)


def serializer_context(request) -> dict:
    return {"request": request, "show_costs": can_see_costs(request.user)}


def protected_objects(instance) -> list[str]:
    collector = NestedObjects(using=router.db_for_write(type(instance)))
    collector.collect([instance])
    return sorted({str(obj) for obj in collector.protected})


def delete_unless_protected(instance) -> Response:
    protected = protected_objects(instance)
    if protected:
        return Response(
            {"detail": "Object is in use.", "protected": protected},
            status=status.HTTP_400_BAD_REQUEST,
        )
    instance.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


class MenuListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("menu")]
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


class MenuDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("menu")]
    serializer_class = None

    def get_queryset(self):
        raise NotImplementedError

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
        return Response(self.serializer_class(instance, context=context).data)

    @transaction.atomic
    def delete(self, request, pk: int):
        return delete_unless_protected(get_object_or_404(self.get_queryset(), pk=pk))


class IngredientCategoryListView(MenuListView):
    serializer_class = IngredientCategorySerializer

    def get_queryset(self):
        return IngredientCategory.objects.all()


class IngredientCategoryDetailView(MenuDetailView):
    serializer_class = IngredientCategorySerializer

    def get_queryset(self):
        return IngredientCategory.objects.all()


class IngredientListView(MenuListView):
    permission_classes = [IsAuthenticated, SectionPermission("menu", also_view=("orders",))]
    serializer_class = IngredientSerializer

    def get_queryset(self):
        return Ingredient.objects.select_related("category")


class IngredientDetailView(MenuDetailView):
    permission_classes = [IsAuthenticated, SectionPermission("menu", also_view=("orders",))]
    serializer_class = IngredientSerializer

    def get_queryset(self):
        return Ingredient.objects.select_related("category")


class AssignIngredientCategoryView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("menu")]

    @transaction.atomic
    def post(self, request):
        serializer = AssignIngredientCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.validated_data["category"]
        category_id = None if category is None else category.pk
        for ingredient in Ingredient.objects.filter(pk__in=serializer.validated_data["ids"]):
            if ingredient.category_id == category_id:
                continue
            ingredient.category = category
            ingredient.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SemiProductCategoryListView(MenuListView):
    serializer_class = SemiProductCategorySerializer

    def get_queryset(self):
        return SemiProductCategory.objects.all()


class SemiProductCategoryDetailView(MenuDetailView):
    serializer_class = SemiProductCategorySerializer

    def get_queryset(self):
        return SemiProductCategory.objects.all()


class SemiProductListView(MenuListView):
    permission_classes = [IsAuthenticated, SectionPermission("menu", also_view=("orders",))]
    serializer_class = SemiProductSerializer

    def get_queryset(self):
        return SemiProduct.objects.select_related("category").prefetch_related("images")


class SemiProductDetailView(MenuDetailView):
    permission_classes = [IsAuthenticated, SectionPermission("menu", also_view=("orders",))]
    serializer_class = SemiProductSerializer

    def get_queryset(self):
        return SemiProduct.objects.select_related("category").prefetch_related("images")


class AssignSemiProductCategoryView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("menu")]

    @transaction.atomic
    def post(self, request):
        serializer = AssignSemiProductCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.validated_data["category"]
        category_id = None if category is None else category.pk
        for semi_product in SemiProduct.objects.filter(pk__in=serializer.validated_data["ids"]):
            if semi_product.category_id == category_id:
                continue
            semi_product.category = category
            semi_product.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ModifierGroupListView(MenuListView):
    permission_classes = [IsAuthenticated, SectionPermission("menu", also_view=("orders",))]
    serializer_class = ModifierGroupSerializer

    def get_queryset(self):
        return ModifierGroup.objects.all()


class ModifierGroupDetailView(MenuDetailView):
    permission_classes = [IsAuthenticated, SectionPermission("menu", also_view=("orders",))]
    serializer_class = ModifierGroupSerializer

    def get_queryset(self):
        return ModifierGroup.objects.all()


class TechCardCategoryListView(MenuListView):
    serializer_class = TechCardCategorySerializer

    def get_queryset(self):
        return TechCardCategory.objects.all()


class TechCardCategoryDetailView(MenuDetailView):
    serializer_class = TechCardCategorySerializer

    def get_queryset(self):
        return TechCardCategory.objects.all()


class TechCardListView(MenuListView):
    permission_classes = [IsAuthenticated, SectionPermission("menu", also_view=("orders", "finished"))]
    serializer_class = TechCardSerializer

    def get_queryset(self):
        return TechCard.objects.select_related("category").prefetch_related("images")


class TechCardDetailView(MenuDetailView):
    permission_classes = [IsAuthenticated, SectionPermission("menu", also_view=("orders",))]
    serializer_class = TechCardSerializer

    def get_queryset(self):
        return TechCard.objects.select_related("category").prefetch_related("images")


class AssignTechCardCategoryView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("menu")]

    @transaction.atomic
    def post(self, request):
        serializer = AssignTechCardCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.validated_data["category"]
        category_id = None if category is None else category.pk
        for tech_card in TechCard.objects.filter(pk__in=serializer.validated_data["ids"]):
            if tech_card.category_id == category_id:
                continue
            tech_card.category = category
            tech_card.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TechCardCostView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, HasPerm("view_costs")]

    def get(self, request, pk: int):
        tech_card = get_object_or_404(TechCard, pk=pk)
        query = TechCardCostQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        weight_kg = query.validated_data.get("weight_kg")
        if tech_card.kind == TechCard.KIND_WEIGHTED and weight_kg is None:
            return Response(
                {"weight_kg": ["Weight is required for a per kilogram tech card."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cost = tech_card_cost(tech_card, query.modifier_pairs(), weight_kg)
        return Response({"cost": str(cost)})


class MissingModifierLinesView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("menu")]

    def get(self, request):
        rows = []
        for tech_card in TechCard.objects.filter(is_active=True):
            for modifier in missing_modifier_compositions(tech_card):
                rows.append(
                    {
                        "tech_card": tech_card.pk,
                        "tech_card_name": tech_card.name,
                        "modifier": modifier.pk,
                        "modifier_name": modifier.name,
                        "group_name": modifier.group.name,
                    }
                )
        return Response(MissingModifierLineSerializer(rows, many=True).data)


class MenuImageCreateView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("menu")]
    parent_model = None
    image_model = None
    parent_attr = ""

    def post(self, request, pk: int):
        parent = get_object_or_404(self.parent_model, pk=pk)
        serializer = MenuImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        position = self.image_model.objects.filter(**{self.parent_attr: parent}).count()
        row = self.image_model.objects.create(
            **{self.parent_attr: parent, "image": serializer.validated_data["image"], "position": position}
        )
        return Response(menu_image_rows([row], request)[0], status=status.HTTP_201_CREATED)


class MenuImageDeleteView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("menu")]
    image_model = None
    parent_attr = ""

    def delete(self, request, pk: int, image_pk: int):
        row = get_object_or_404(self.image_model, pk=image_pk, **{f"{self.parent_attr}_id": pk})
        row.image.delete(save=False)
        row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SemiProductImageCreateView(MenuImageCreateView):
    parent_model = SemiProduct
    image_model = SemiProductImage
    parent_attr = "semi_product"


class SemiProductImageDeleteView(MenuImageDeleteView):
    image_model = SemiProductImage
    parent_attr = "semi_product"


class TechCardImageCreateView(MenuImageCreateView):
    parent_model = TechCard
    image_model = TechCardImage
    parent_attr = "tech_card"


class TechCardImageDeleteView(MenuImageDeleteView):
    image_model = TechCardImage
    parent_attr = "tech_card"


class CatalogOptionListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("menu", also_view=("orders",))]

    def get(self, request):
        options = Option.objects.select_related("group").order_by("group__name", "position", "id")
        modifier_by_option = dict(
            Modifier.objects.filter(catalog_option__isnull=False).values_list("catalog_option_id", "id")
        )
        serializer = CatalogOptionSerializer(
            options,
            many=True,
            context={"modifier_by_option": modifier_by_option},
        )
        return Response(serializer.data)
