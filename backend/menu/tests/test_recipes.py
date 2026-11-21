import tempfile
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError as ApiValidationError
from rest_framework.test import APIClient

from accounts.permissions import grant
from catalog.models import Category, Product
from crm.models import CrmOrder, CrmOrderItemLine
from crm.serializers import crm_item_sale_price
from menu.models import (
    UNIT_GRAM,
    UNIT_MILLILITER,
    UNIT_PIECE,
    Ingredient,
    Modifier,
    ModifierGroup,
    SemiProduct,
    SemiProductCategory,
    SemiProductImage,
    SemiProductLine,
    TechCard,
    TechCardCategory,
    TechCardImage,
    TechCardLine,
    TechCardModifierGroup,
    TechCardModifierLine,
    TechCardSection,
)
from menu.recipes import (
    component_quantity,
    expand_order,
    expand_order_item,
    expand_semi_product,
    order_cost,
    semi_product_cost,
    stock_line_cost,
    tech_card_cost,
    tech_card_cost_range,
    validate_order_item,
)
from menu.serializers import ModifierGroupSerializer, RecipeLineSerializer, TechCardSerializer
from menu.tests.fixtures import MenuFixture, add_item, make_crm_order


class ExpandOrderItemTests(TestCase):
    maxDiff = None

    def setUp(self):
        self.menu = MenuFixture()

    def test_weighted_card_scales_base_and_filling_but_not_photo_print(self):
        menu = self.menu
        needs = expand_order_item(
            menu.cake,
            Decimal("2.5"),
            2,
            [(menu.raspberry_filling, 1), (menu.photo, 1), (menu.berries, 2)],
            [],
        )
        self.assertEqual(
            needs,
            {
                menu.flour: Decimal("1500"),
                menu.sugar: Decimal("1000"),
                menu.cream: Decimal("1500"),
                menu.raspberry: Decimal("1000"),
                menu.paper: Decimal("2"),
                menu.ink: Decimal("4"),
            },
        )

    def test_loss_quantity_increases_gross_quantity(self):
        TechCardLine.objects.filter(tech_card=self.menu.bento).update(loss_quantity=Decimal("25"))
        needs = expand_order_item(self.menu.bento, None, 1, [], [])
        self.assertEqual(needs, {self.menu.flour: Decimal("125")})

    def test_weighted_card_scales_from_its_basis_weight(self):
        menu = self.menu
        menu.cake.basis_weight_kg = Decimal("1.5")
        menu.cake.save(update_fields=["basis_weight_kg"])
        needs = expand_order_item(
            menu.cake,
            Decimal("3"),
            1,
            [(menu.raspberry_filling, 1)],
            [],
        )
        self.assertEqual(
            needs,
            {
                menu.flour: Decimal("600"),
                menu.sugar: Decimal("400"),
                menu.cream: Decimal("600"),
                menu.raspberry: Decimal("200"),
            },
        )

    def test_piece_card_multiplies_by_item_quantity(self):
        needs = expand_order_item(self.menu.bento, None, 3, [], [])
        self.assertEqual(needs, {self.menu.flour: Decimal("300")})

    def test_piece_card_scales_from_its_basis_quantity(self):
        menu = self.menu
        menu.bento.basis_quantity = 8
        menu.bento.save(update_fields=["basis_quantity"])
        menu.bento.lines.update(quantity=Decimal("21"))
        needs = expand_order_item(menu.bento, None, 4, [], [])
        self.assertEqual(needs, {menu.flour: Decimal("10.5")})

    def test_free_item_lines_are_added_as_is(self):
        needs = expand_order_item(None, None, 2, [], [(self.menu.sugar, Decimal("50"))])
        self.assertEqual(needs, {self.menu.sugar: Decimal("50")})

    def test_manual_lines_are_added_to_tech_card_composition(self):
        needs = expand_order_item(self.menu.bento, None, 1, [], [(self.menu.flour, Decimal("20"))])
        self.assertEqual(needs, {self.menu.flour: Decimal("120")})

    def test_produced_semi_product_stays_whole(self):
        needs = expand_order_item(self.menu.frozen_cake, None, 2, [], [])
        self.assertEqual(needs, {self.menu.frozen_sponge: Decimal("800")})

    def test_not_produced_semi_product_in_manual_line_is_expanded(self):
        needs = expand_order_item(None, None, 1, [], [(self.menu.sponge, Decimal("500"))])
        self.assertEqual(needs, {self.menu.flour: Decimal("300"), self.menu.sugar: Decimal("200")})

    def test_piece_extra_tech_card_adds_base_needs(self):
        needs = expand_order_item(self.menu.bento, None, 2, [], [(self.menu.frozen_cake, Decimal("3"))])
        self.assertEqual(needs[self.menu.flour], Decimal("200"))
        self.assertEqual(needs[self.menu.frozen_sponge], Decimal("1200"))

    def test_weighted_extra_tech_card_adds_base_needs_in_grams(self):
        needs = expand_order_item(self.menu.bento, None, 1, [], [(self.menu.cake, Decimal("500"))])
        self.assertEqual(needs[self.menu.flour], Decimal("250"))
        self.assertEqual(needs[self.menu.sugar], Decimal("100"))
        self.assertEqual(needs[self.menu.cream], Decimal("150"))
        self.assertNotIn(self.menu.raspberry, needs)


class ExpandSemiProductTests(TestCase):
    def test_proportional_to_yield(self):
        menu = MenuFixture()
        self.assertEqual(
            expand_semi_product(menu.frozen_sponge, Decimal("2000")),
            {menu.flour: Decimal("1200"), menu.sugar: Decimal("800")},
        )


class ValidateOrderItemTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()

    def test_weighted_card_requires_weight(self):
        with self.assertRaises(ValidationError):
            validate_order_item(self.menu.cake, None, [(self.menu.raspberry_filling, 1)])

    def test_modifier_from_unlinked_group_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_order_item(
                self.menu.cake,
                Decimal("1"),
                [(self.menu.raspberry_filling, 1), (self.menu.balloon, 1)],
            )

    def test_single_group_allows_one_modifier(self):
        with self.assertRaises(ValidationError):
            validate_order_item(
                self.menu.cake,
                Decimal("1"),
                [(self.menu.raspberry_filling, 1), (self.menu.mango_filling, 1)],
            )

    def test_required_group_must_be_selected(self):
        with self.assertRaises(ValidationError):
            validate_order_item(self.menu.cake, Decimal("1"), [(self.menu.photo, 1)])

    def test_item_without_tech_card_cannot_have_modifiers(self):
        with self.assertRaises(ValidationError):
            validate_order_item(None, None, [(self.menu.photo, 1)])

    def test_valid_item_passes(self):
        validate_order_item(
            self.menu.cake,
            Decimal("1.5"),
            [(self.menu.raspberry_filling, 1), (self.menu.photo, 1), (self.menu.berries, 1)],
        )


class CostTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()

    def test_tech_card_cost_per_kilogram(self):
        self.assertEqual(tech_card_cost(self.menu.cake, [], Decimal("1")), Decimal("10.00"))

    def test_section_line_is_included_in_needs_and_cost(self):
        section = TechCardSection.objects.create(
            tech_card=self.menu.cake,
            name="Syrup",
            method="Boil.",
            position=0,
        )
        TechCardLine.objects.create(
            tech_card=self.menu.cake,
            section=section,
            ingredient=self.menu.sugar,
            quantity=Decimal("100"),
            quantity_unit=UNIT_GRAM,
        )
        needs = expand_order_item(self.menu.cake, Decimal("1"), 1, [], [])
        self.assertEqual(needs[self.menu.sugar], Decimal("300"))
        self.assertEqual(tech_card_cost(self.menu.cake, [], Decimal("1")), Decimal("10.50"))

    def test_tech_card_cost_with_modifiers(self):
        cost = tech_card_cost(
            self.menu.cake,
            [(self.menu.raspberry_filling, 1), (self.menu.photo, 1)],
            Decimal("2"),
        )
        self.assertEqual(cost, Decimal("27.70"))

    def test_tech_card_cost_range_includes_modifiers(self):
        low, high = tech_card_cost_range(self.menu.cake, Decimal("1"))
        self.assertEqual(low, Decimal("10.00"))
        self.assertEqual(high, Decimal("13.00"))

    def test_tech_card_without_modifiers_has_equal_bounds(self):
        low, high = tech_card_cost_range(self.menu.bento, None)
        self.assertEqual(low, high)
        self.assertEqual(low, tech_card_cost(self.menu.bento, [], None))

    def test_cost_range_required_multi_counts_only_minimum(self):
        group = ModifierGroup.objects.create(
            name="Toppings",
            selection_type=ModifierGroup.SELECTION_MULTI,
            is_required=True,
            min_selections=2,
        )
        cheap = Modifier.objects.create(group=group, name="Cheap")
        mid = Modifier.objects.create(group=group, name="Mid")
        dear = Modifier.objects.create(group=group, name="Dear")
        TechCardModifierGroup.objects.create(tech_card=self.menu.bento, group=group, position=0)
        for modifier, grams in ((cheap, Decimal("100")), (mid, Decimal("200")), (dear, Decimal("400"))):
            TechCardModifierLine.objects.create(
                tech_card=self.menu.bento,
                modifier=modifier,
                ingredient=self.menu.flour,
                quantity=grams,
                quantity_unit=UNIT_GRAM,
                scales_by_weight=False,
            )
        low, high = tech_card_cost_range(self.menu.bento, None)
        self.assertEqual(low, Decimal("4.00"))
        self.assertEqual(high, Decimal("7.00"))

    def test_cost_range_ignores_optional_global_group(self):
        self.menu.extras.is_global = True
        self.menu.extras.save(update_fields=["is_global"])
        self.menu.balloon.ingredient = self.menu.paper
        self.menu.balloon.save(update_fields=["ingredient"])
        low, high = tech_card_cost_range(self.menu.bento, None)
        self.assertEqual(low, Decimal("1.00"))
        self.assertEqual(high, Decimal("1.00"))

    def test_cost_range_includes_required_global_single(self):
        self.menu.extras.selection_type = ModifierGroup.SELECTION_SINGLE
        self.menu.extras.is_global = True
        self.menu.extras.is_required = True
        self.menu.extras.save(update_fields=["selection_type", "is_global", "is_required"])
        self.menu.balloon.ingredient = self.menu.paper
        self.menu.balloon.save(update_fields=["ingredient"])
        Modifier.objects.create(group=self.menu.extras, name="Candle", ingredient=self.menu.ink)
        low, high = tech_card_cost_range(self.menu.bento, None)
        self.assertEqual(low, Decimal("1.10"))
        self.assertEqual(high, Decimal("2.50"))

    def test_order_cost_sums_items(self):
        order = make_crm_order(CrmOrder.STATUS_NEW)
        add_item(order, self.menu.cake, Decimal("1"), 1, [(self.menu.raspberry_filling, 1)])
        item = add_item(order, None, None, 1, [])
        CrmOrderItemLine.objects.create(item=item, ingredient=self.menu.paper, quantity=Decimal("2"))
        self.assertEqual(order_cost(order), Decimal("16.00"))

    def test_expand_order_without_items_is_empty(self):
        self.assertEqual(expand_order(make_crm_order(CrmOrder.STATUS_NEW)), {})


class GramsConversionTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()

    def test_grams_of_milliliters_convert_before_cost(self):
        self.menu.cream.grams_per_unit = Decimal("0.5")
        self.menu.cream.save(update_fields=["grams_per_unit"])
        TechCardLine.objects.filter(tech_card=self.menu.cake, ingredient=self.menu.cream).update(
            quantity_unit=UNIT_GRAM
        )
        needs = expand_order_item(self.menu.cake, Decimal("1"), 1, [], [])
        self.assertEqual(needs[self.menu.cream], Decimal("600"))
        self.assertEqual(tech_card_cost(self.menu.cake, [], Decimal("1")), Decimal("16.00"))

    def test_loss_is_applied_in_grams_before_conversion(self):
        self.menu.cream.grams_per_unit = Decimal("2")
        self.menu.cream.save(update_fields=["grams_per_unit"])
        TechCardLine.objects.filter(tech_card=self.menu.cake, ingredient=self.menu.cream).update(
            quantity=Decimal("100"),
            quantity_unit=UNIT_GRAM,
            loss_quantity=Decimal("25"),
        )
        needs = expand_order_item(self.menu.cake, Decimal("1"), 1, [], [])
        self.assertEqual(needs[self.menu.cream], Decimal("62.5"))

    def test_semi_product_cost_uses_ingredient_price_when_stock_cost_is_zero(self):
        oil = Ingredient.objects.create(
            name="Oil",
            unit=UNIT_MILLILITER,
            avg_cost=Decimal("0.01"),
            grams_per_unit=Decimal("1"),
        )
        batter = SemiProduct.objects.create(
            name="Batter",
            unit=UNIT_GRAM,
            yield_quantity=Decimal("1000"),
            is_produced=True,
            avg_cost=Decimal("0"),
        )
        SemiProductLine.objects.create(
            parent=batter,
            ingredient=oil,
            quantity=Decimal("100"),
            quantity_unit=UNIT_GRAM,
        )
        self.assertEqual(semi_product_cost(batter), Decimal("1.00"))

    def test_semi_product_cost_explodes_nested_produced_semi_product(self):
        oil = Ingredient.objects.create(
            name="Oil",
            unit=UNIT_MILLILITER,
            avg_cost=Decimal("0.01"),
            grams_per_unit=Decimal("1"),
        )
        batter = SemiProduct.objects.create(
            name="Batter",
            unit=UNIT_GRAM,
            yield_quantity=Decimal("1000"),
            is_produced=True,
            avg_cost=Decimal("0"),
        )
        SemiProductLine.objects.create(
            parent=batter,
            ingredient=oil,
            quantity=Decimal("100"),
            quantity_unit=UNIT_GRAM,
        )
        cake = SemiProduct.objects.create(
            name="Cake base",
            unit=UNIT_GRAM,
            yield_quantity=Decimal("500"),
            is_produced=False,
        )
        SemiProductLine.objects.create(
            parent=cake,
            semi_product=batter,
            quantity=Decimal("500"),
            quantity_unit=UNIT_GRAM,
        )
        self.assertEqual(semi_product_cost(cake), Decimal("0.50"))

    def test_semi_line_in_grams_scales_with_yield(self):
        oil = Ingredient.objects.create(
            name="Oil",
            unit=UNIT_MILLILITER,
            avg_cost=Decimal("0.01"),
            grams_per_unit=Decimal("1"),
        )
        batter = SemiProduct.objects.create(
            name="Batter",
            unit=UNIT_GRAM,
            yield_quantity=Decimal("1000"),
            is_produced=False,
        )
        SemiProductLine.objects.create(
            parent=batter,
            ingredient=oil,
            quantity=Decimal("100"),
            quantity_unit=UNIT_GRAM,
        )
        self.assertEqual(expand_semi_product(batter, Decimal("500")), {oil: Decimal("50")})

    def test_grams_of_non_gram_semi_product_are_rejected(self):
        juice = SemiProduct.objects.create(
            name="Juice",
            unit=UNIT_MILLILITER,
            yield_quantity=Decimal("100"),
            is_produced=False,
        )
        with self.assertRaises(ValidationError):
            component_quantity(juice, Decimal("10"), UNIT_GRAM)

    def test_mismatched_units_are_rejected(self):
        with self.assertRaises(ValidationError):
            component_quantity(self.menu.paper, Decimal("1"), UNIT_MILLILITER)
        serializer = RecipeLineSerializer(
            data={
                "ingredient": self.menu.paper.pk,
                "semi_product": None,
                "quantity": "1",
                "loss_quantity": "0",
                "quantity_unit": UNIT_MILLILITER,
            }
        )
        self.assertFalse(serializer.is_valid())


class LineCostApiTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        self.client = APIClient()
        self.staff = User.objects.create_user("chef", password="x")
        self.admin = User.objects.create_user("boss", password="x")
        grant(self.staff, "view_menu")
        grant(self.admin, "view_menu", "view_costs")
        section = TechCardSection.objects.create(
            tech_card=self.menu.cake,
            name="Syrup",
            method="Boil.",
            position=0,
        )
        TechCardLine.objects.create(
            tech_card=self.menu.cake,
            section=section,
            ingredient=self.menu.sugar,
            quantity=Decimal("100"),
            quantity_unit=UNIT_GRAM,
        )
        self.menu.frozen_sponge.avg_cost = Decimal("0.02")
        self.menu.frozen_sponge.save(update_fields=["avg_cost"])
        TechCardLine.objects.create(
            tech_card=self.menu.cake,
            semi_product=self.menu.frozen_sponge,
            quantity=Decimal("100"),
            quantity_unit=UNIT_GRAM,
        )
        self.layered = SemiProduct.objects.create(
            name="Layered",
            unit=UNIT_GRAM,
            yield_quantity=Decimal("500"),
            is_produced=False,
        )
        SemiProductLine.objects.create(
            parent=self.layered,
            semi_product=self.menu.frozen_sponge,
            quantity=Decimal("500"),
            quantity_unit=UNIT_GRAM,
        )

    def test_finance_admin_sees_line_costs_that_sum_to_the_total(self):
        self.client.force_authenticate(self.admin)
        card = self.client.get(f"/api/menu/tech-cards/{self.menu.cake.pk}/")
        self.assertEqual(card.status_code, 200, card.content)
        body = card.json()
        lines = body["lines"] + [line for section in body["sections"] for line in section["lines"]]
        self.assertEqual(sum(Decimal(line["cost"]) for line in lines), Decimal(body["base_cost"]))
        self.assertEqual(Decimal(body["cost_min"]), Decimal("12.50"))
        self.assertEqual(Decimal(body["cost_max"]), Decimal("15.50"))
        frozen = next(line for line in body["lines"] if line["semi_product"] == self.menu.frozen_sponge.pk)
        self.assertEqual(Decimal(frozen["cost"]), Decimal("2.00"))
        self.assertTrue(all("cost" in line for line in body["modifier_lines"]))

        sponge = self.client.get(f"/api/menu/semi-products/{self.menu.sponge.pk}/")
        self.assertEqual(sponge.status_code, 200, sponge.content)
        sponge_body = sponge.json()
        self.assertEqual(
            sum(Decimal(line["cost"]) for line in sponge_body["lines"]),
            Decimal(sponge_body["cost"]),
        )

        layered = self.client.get(f"/api/menu/semi-products/{self.layered.pk}/")
        self.assertEqual(layered.status_code, 200, layered.content)
        layered_body = layered.json()
        self.assertEqual(Decimal(layered_body["lines"][0]["cost"]), Decimal("4.00"))
        self.assertEqual(
            sum(Decimal(line["cost"]) for line in layered_body["lines"]),
            Decimal(layered_body["cost"]),
        )

    def test_staff_does_not_see_line_costs(self):
        self.client.force_authenticate(self.staff)
        card = self.client.get(f"/api/menu/tech-cards/{self.menu.cake.pk}/")
        self.assertEqual(card.status_code, 200, card.content)
        body = card.json()
        self.assertNotIn("base_cost", body)
        self.assertNotIn("cost_min", body)
        self.assertNotIn("cost_max", body)
        for line in body["lines"] + body["modifier_lines"]:
            self.assertNotIn("cost", line)
        for section in body["sections"]:
            for line in section["lines"]:
                self.assertNotIn("cost", line)
        sponge = self.client.get(f"/api/menu/semi-products/{self.menu.sponge.pk}/")
        self.assertEqual(sponge.status_code, 200, sponge.content)
        sponge_body = sponge.json()
        self.assertNotIn("cost", sponge_body)
        for line in sponge_body["lines"]:
            self.assertNotIn("cost", line)


class NestedTechCardTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()

    def _layer(self, sale_price: Decimal | None) -> TechCard:
        layer = TechCard.objects.create(
            name="Layer",
            kind=TechCard.KIND_WEIGHTED,
            basis_weight_kg=Decimal("1"),
            sale_price=sale_price,
        )
        TechCardLine.objects.create(
            tech_card=layer,
            ingredient=self.menu.flour,
            quantity=Decimal("100"),
            quantity_unit=UNIT_GRAM,
        )
        section = TechCardSection.objects.create(tech_card=layer, name="Soak", method="", position=0)
        TechCardLine.objects.create(
            tech_card=layer,
            section=section,
            ingredient=self.menu.sugar,
            quantity=Decimal("50"),
            quantity_unit=UNIT_GRAM,
        )
        return layer

    def _attach(self, parent: TechCard, nested: TechCard, quantity: Decimal, unit: str, scales: bool) -> Modifier:
        modifier = Modifier.objects.create(group=self.menu.extras, name=nested.name, nested_tech_card=nested)
        TechCardModifierGroup.objects.create(tech_card=parent, group=self.menu.extras, position=0)
        TechCardModifierLine.objects.create(
            tech_card=parent,
            modifier=modifier,
            nested_tech_card=nested,
            quantity=quantity,
            quantity_unit=unit,
            scales_by_weight=scales,
        )
        return modifier

    def test_piece_nested_card_adds_base_needs_only(self):
        topper = TechCard.objects.create(name="Topper", kind=TechCard.KIND_PIECE, basis_quantity=1)
        TechCardLine.objects.create(
            tech_card=topper,
            ingredient=self.menu.paper,
            quantity=Decimal("1"),
            quantity_unit=UNIT_PIECE,
        )
        TechCardModifierGroup.objects.create(tech_card=topper, group=self.menu.decor, position=0)
        TechCardModifierLine.objects.create(
            tech_card=topper,
            modifier=self.menu.photo,
            ingredient=self.menu.ink,
            quantity=Decimal("5"),
            quantity_unit=UNIT_MILLILITER,
            scales_by_weight=False,
        )
        modifier = self._attach(self.menu.cake, topper, Decimal("2"), UNIT_PIECE, False)
        needs = expand_order_item(self.menu.cake, Decimal("2"), 1, [(modifier, 3)], [])
        self.assertEqual(needs[self.menu.flour], Decimal("600"))
        self.assertEqual(needs[self.menu.sugar], Decimal("400"))
        self.assertEqual(needs[self.menu.cream], Decimal("600"))
        self.assertEqual(needs[self.menu.paper], Decimal("6"))
        self.assertNotIn(self.menu.ink, needs)
        self.assertEqual(
            tech_card_cost(self.menu.cake, [(modifier, 3)], Decimal("2")),
            Decimal("29.00"),
        )

    def test_weighted_nested_card_scales_base_lines_and_sections(self):
        layer = self._layer(Decimal("40.00"))
        modifier = self._attach(self.menu.bento, layer, Decimal("250"), UNIT_GRAM, True)
        needs = expand_order_item(self.menu.bento, None, 2, [(modifier, 1)], [])
        self.assertEqual(needs[self.menu.flour], Decimal("250"))
        self.assertEqual(needs[self.menu.sugar], Decimal("25"))
        low, high = tech_card_cost_range(self.menu.bento, None)
        self.assertEqual(low, Decimal("1.00"))
        self.assertEqual(high, Decimal("1.00"))

    def test_sale_price_includes_nested_card_and_skips_missing_price(self):
        layer = self._layer(Decimal("40.00"))
        modifier = self._attach(self.menu.cake, layer, Decimal("250"), UNIT_GRAM, True)
        self.menu.cake.sale_price = Decimal("60.00")
        price = crm_item_sale_price(self.menu.cake, 1, Decimal("2"), [(modifier, 1)], [])
        self.assertEqual(price, Decimal("140.00"))
        layer.sale_price = None
        layer.save(update_fields=["sale_price"])
        price = crm_item_sale_price(self.menu.cake, 1, Decimal("2"), [(modifier, 1)], [])
        self.assertEqual(price, Decimal("120.00"))

    def test_sale_price_adds_extra_tech_card_quantity(self):
        self.menu.bento.sale_price = Decimal("20.00")
        layer = self._layer(Decimal("40.00"))
        price = crm_item_sale_price(
            self.menu.bento,
            2,
            None,
            [],
            [{"tech_card": layer, "quantity": Decimal("500")}],
        )
        self.assertEqual(price, Decimal("60.00"))
        topper = TechCard.objects.create(
            name="Topper",
            kind=TechCard.KIND_PIECE,
            basis_quantity=1,
            sale_price=Decimal("15.00"),
        )
        price = crm_item_sale_price(
            self.menu.bento,
            2,
            None,
            [],
            [{"tech_card": topper, "quantity": Decimal("3")}],
        )
        self.assertEqual(price, Decimal("85.00"))
        topper.sale_price = None
        topper.save(update_fields=["sale_price"])
        price = crm_item_sale_price(
            self.menu.bento,
            2,
            None,
            [],
            [{"tech_card": topper, "quantity": Decimal("3")}],
        )
        self.assertEqual(price, Decimal("40.00"))

    def _card_payload(self, card: TechCard, modifier: Modifier, nested: TechCard) -> dict:
        return {
            "name": card.name,
            "category": None,
            "kind": card.kind,
            "basis_weight_kg": None if card.basis_weight_kg is None else str(card.basis_weight_kg),
            "basis_quantity": card.basis_quantity,
            "method": "",
            "is_active": True,
            "lines": [],
            "sections": [],
            "modifier_groups": [{"group": modifier.group_id, "is_required": None}],
            "modifier_lines": [
                {
                    "modifier": modifier.pk,
                    "ingredient": None,
                    "semi_product": None,
                    "nested_tech_card": nested.pk,
                    "quantity": "1",
                    "quantity_unit": nested.unit,
                    "loss_quantity": "0",
                    "scales_by_weight": False,
                }
            ],
        }

    def test_self_reference_is_rejected(self):
        card = TechCard.objects.create(name="Loop", kind=TechCard.KIND_PIECE, basis_quantity=1)
        modifier = Modifier.objects.create(group=self.menu.extras, name="Loop")
        serializer = TechCardSerializer(card, data=self._card_payload(card, modifier, card))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(ApiValidationError):
            serializer.save()

    def test_transitive_cycle_is_rejected(self):
        first = TechCard.objects.create(name="First", kind=TechCard.KIND_PIECE, basis_quantity=1)
        second = TechCard.objects.create(name="Second", kind=TechCard.KIND_PIECE, basis_quantity=1)
        to_first = Modifier.objects.create(group=self.menu.extras, name="To first")
        to_second = Modifier.objects.create(group=self.menu.filling, name="To second")
        saved = TechCardSerializer(second, data=self._card_payload(second, to_first, first))
        self.assertTrue(saved.is_valid(), saved.errors)
        saved.save()
        self.assertEqual(second.modifier_lines.get().nested_tech_card_id, first.pk)
        cycle = TechCardSerializer(first, data=self._card_payload(first, to_second, second))
        self.assertTrue(cycle.is_valid(), cycle.errors)
        with self.assertRaises(ApiValidationError):
            cycle.save()

    def test_modifier_with_two_defaults_is_rejected(self):
        serializer = ModifierGroupSerializer(
            self.menu.extras,
            data={
                "name": self.menu.extras.name,
                "selection_type": "multi",
                "is_required": False,
                "is_global": False,
                "has_quantity": True,
                "categories": [],
                "min_selections": 0,
                "max_selections": None,
                "position": 0,
                "priority": 0,
                "modifiers": [
                    {
                        "id": self.menu.balloon.pk,
                        "name": "Balloon",
                        "catalog_option": None,
                        "ingredient": self.menu.flour.pk,
                        "semi_product": self.menu.sponge.pk,
                        "nested_tech_card": None,
                        "default_modifier": None,
                        "is_active": True,
                    }
                ],
            },
        )
        self.assertFalse(serializer.is_valid())


class NestedTechCardLineTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        self.client = APIClient()
        self.staff = User.objects.create_user("chef", password="x")
        grant(self.staff, "edit_menu")
        self.client.force_authenticate(self.staff)
        self.filling = TechCard.objects.create(name="Filling card", kind=TechCard.KIND_PIECE, basis_quantity=1)
        TechCardLine.objects.create(
            tech_card=self.filling,
            ingredient=self.menu.flour,
            quantity=Decimal("100"),
            quantity_unit=UNIT_GRAM,
        )
        self.syrup = TechCard.objects.create(
            name="Syrup card",
            kind=TechCard.KIND_WEIGHTED,
            basis_weight_kg=Decimal("1"),
        )
        TechCardLine.objects.create(
            tech_card=self.syrup,
            ingredient=self.menu.sugar,
            quantity=Decimal("200"),
            quantity_unit=UNIT_GRAM,
        )

    def _payload(self, name: str, lines: list[dict], sections: list[dict]) -> dict:
        return {
            "name": name,
            "category": None,
            "kind": TechCard.KIND_PIECE,
            "basis_weight_kg": None,
            "basis_quantity": 1,
            "method": "",
            "is_active": True,
            "lines": lines,
            "sections": sections,
            "modifier_groups": [],
            "modifier_lines": [],
        }

    def _nested_line(self, card: TechCard, quantity: str) -> dict:
        return {
            "ingredient": None,
            "semi_product": None,
            "nested_tech_card": card.pk,
            "quantity": quantity,
            "quantity_unit": card.unit,
            "loss_quantity": "0",
        }

    def test_base_and_section_lines_save_a_nested_tech_card(self):
        response = self.client.post(
            "/api/menu/tech-cards/",
            self._payload(
                "Assembled",
                [self._nested_line(self.filling, "2")],
                [
                    {
                        "name": "Syrup",
                        "method": "",
                        "lines": [self._nested_line(self.syrup, "500")],
                    }
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["lines"][0]["nested_tech_card"], self.filling.pk)
        self.assertIsNone(body["lines"][0]["ingredient"])
        self.assertIsNone(body["lines"][0]["semi_product"])
        self.assertEqual(body["sections"][0]["lines"][0]["nested_tech_card"], self.syrup.pk)
        parent = TechCard.objects.get(pk=body["id"])
        needs = expand_order_item(parent, None, 1, [], [])
        self.assertEqual(needs[self.menu.flour], Decimal("200"))
        self.assertEqual(needs[self.menu.sugar], Decimal("100"))
        self.assertEqual(tech_card_cost(parent, [], None), Decimal("2.50"))

    def test_line_self_reference_is_rejected(self):
        card = TechCard.objects.create(name="Loop line", kind=TechCard.KIND_PIECE, basis_quantity=1)
        response = self.client.put(
            f"/api/menu/tech-cards/{card.pk}/",
            self._payload(
                card.name,
                [],
                [{"name": "Loop", "method": "", "lines": [self._nested_line(card, "1")]}],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_transitive_line_cycle_is_rejected(self):
        first = TechCard.objects.create(name="First line", kind=TechCard.KIND_PIECE, basis_quantity=1)
        second = TechCard.objects.create(name="Second line", kind=TechCard.KIND_PIECE, basis_quantity=1)
        saved = self.client.put(
            f"/api/menu/tech-cards/{second.pk}/",
            self._payload(second.name, [self._nested_line(first, "1")], []),
            format="json",
        )
        self.assertEqual(saved.status_code, 200, saved.content)
        cycle = self.client.put(
            f"/api/menu/tech-cards/{first.pk}/",
            self._payload(first.name, [self._nested_line(second, "1")], []),
            format="json",
        )
        self.assertEqual(cycle.status_code, 400, cycle.content)


class GlobalModifierGroupTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        self.menu.extras.is_global = True
        self.menu.extras.is_required = True
        self.menu.extras.save()
        self.menu.balloon.ingredient = self.menu.paper
        self.menu.balloon.save()

    def test_required_global_group_must_be_selected(self):
        with self.assertRaises(ValidationError):
            validate_order_item(self.menu.bento, None, [])

    def test_extra_selection_in_global_group_is_rejected(self):
        self.menu.extras.selection_type = ModifierGroup.SELECTION_SINGLE
        self.menu.extras.save()
        candle = Modifier.objects.create(group=self.menu.extras, name="Candle", ingredient=self.menu.paper)
        with self.assertRaises(ValidationError):
            validate_order_item(self.menu.bento, None, [(self.menu.balloon, 1), (candle, 1)])

    def test_group_without_quantity_rejects_more_than_one(self):
        self.menu.extras.has_quantity = False
        self.menu.extras.save()
        with self.assertRaises(ValidationError):
            validate_order_item(self.menu.bento, None, [(self.menu.balloon, 2)])

    def test_consumption_uses_modifier_quantity_not_weight(self):
        needs = expand_order_item(
            self.menu.cake,
            Decimal("2"),
            3,
            [(self.menu.raspberry_filling, 1), (self.menu.balloon, 4)],
            [],
        )
        self.assertEqual(needs[self.menu.paper], Decimal("12"))

    def test_explicit_link_overrides_global_default(self):
        TechCardModifierGroup.objects.create(tech_card=self.menu.bento, group=self.menu.extras, position=0)
        TechCardModifierLine.objects.create(
            tech_card=self.menu.bento,
            modifier=self.menu.balloon,
            ingredient=self.menu.ink,
            quantity=Decimal("5"),
            quantity_unit=UNIT_MILLILITER,
            scales_by_weight=False,
        )
        needs = expand_order_item(self.menu.bento, None, 2, [(self.menu.balloon, 1)], [])
        self.assertEqual(needs[self.menu.ink], Decimal("10"))
        self.assertNotIn(self.menu.paper, needs)


class CategoryModifierGroupTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        self.cakes = TechCardCategory.objects.create(name="Cakes")
        self.bentos = TechCardCategory.objects.create(name="Bentos")
        self.menu.frozen_cake.category = self.cakes
        self.menu.frozen_cake.save(update_fields=["category"])
        self.menu.bento.category = self.bentos
        self.menu.bento.save(update_fields=["category"])
        self.menu.extras.is_required = True
        self.menu.extras.save(update_fields=["is_required"])
        self.menu.extras.categories.add(self.cakes)
        self.menu.balloon.ingredient = self.menu.paper
        self.menu.balloon.save(update_fields=["ingredient"])

    def test_required_category_group_must_be_selected(self):
        with self.assertRaises(ValidationError):
            validate_order_item(self.menu.frozen_cake, None, [])

    def test_other_category_is_not_affected(self):
        validate_order_item(self.menu.bento, None, [])

    def test_card_without_category_is_not_affected(self):
        plain = TechCard.objects.create(name="Plain", kind=TechCard.KIND_PIECE, basis_quantity=1)
        validate_order_item(plain, None, [])

    def test_explicit_link_overrides_category_default(self):
        TechCardModifierGroup.objects.create(tech_card=self.menu.frozen_cake, group=self.menu.extras, position=0)
        TechCardModifierLine.objects.create(
            tech_card=self.menu.frozen_cake,
            modifier=self.menu.balloon,
            ingredient=self.menu.ink,
            quantity=Decimal("5"),
            quantity_unit=UNIT_MILLILITER,
            scales_by_weight=False,
        )
        needs = expand_order_item(self.menu.frozen_cake, None, 2, [(self.menu.balloon, 1)], [])
        self.assertEqual(needs[self.menu.ink], Decimal("10"))
        self.assertNotIn(self.menu.paper, needs)

    def test_global_group_rejects_categories(self):
        serializer = ModifierGroupSerializer(
            self.menu.extras,
            data={
                "name": self.menu.extras.name,
                "selection_type": "multi",
                "is_required": True,
                "is_global": True,
                "has_quantity": True,
                "categories": [self.cakes.pk],
                "min_selections": 0,
                "max_selections": None,
                "position": 0,
                "priority": 0,
                "modifiers": [
                    {
                        "id": self.menu.balloon.pk,
                        "name": "Balloon",
                        "catalog_option": None,
                        "ingredient": self.menu.paper.pk,
                        "semi_product": None,
                        "nested_tech_card": None,
                        "default_modifier": None,
                        "is_active": True,
                    }
                ],
            },
        )
        self.assertFalse(serializer.is_valid())


class ModifierDefaultTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()

    def _body(self, group: ModifierGroup, modifiers: list[dict]) -> dict:
        return {
            "name": group.name,
            "selection_type": group.selection_type,
            "is_required": group.is_required,
            "is_global": group.is_global,
            "has_quantity": group.has_quantity,
            "categories": [],
            "min_selections": group.min_selections,
            "max_selections": group.max_selections,
            "priority": group.priority,
            "position": group.position,
            "modifiers": modifiers,
        }

    def _row(self, modifier: Modifier, default_modifier: Modifier | None) -> dict:
        return {
            "id": modifier.pk,
            "name": modifier.name,
            "catalog_option": None,
            "ingredient": None,
            "semi_product": None,
            "nested_tech_card": None,
            "default_modifier": None if default_modifier is None else default_modifier.pk,
            "is_active": True,
        }

    def test_saves_default_modifier_from_another_group(self):
        serializer = ModifierGroupSerializer(
            self.menu.filling,
            data=self._body(
                self.menu.filling,
                [
                    self._row(self.menu.raspberry_filling, self.menu.photo),
                    self._row(self.menu.mango_filling, None),
                ],
            ),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.menu.raspberry_filling.refresh_from_db()
        self.assertEqual(self.menu.raspberry_filling.default_modifier_id, self.menu.photo.pk)
        saved = {row["id"]: row for row in serializer.data["modifiers"]}
        self.assertEqual(saved[self.menu.raspberry_filling.pk]["default_modifier"], self.menu.photo.pk)

    def test_rejects_default_in_the_same_group(self):
        serializer = ModifierGroupSerializer(
            self.menu.filling,
            data=self._body(
                self.menu.filling,
                [
                    self._row(self.menu.raspberry_filling, self.menu.mango_filling),
                    self._row(self.menu.mango_filling, None),
                ],
            ),
        )
        self.assertFalse(serializer.is_valid())

    def test_rejects_default_to_itself(self):
        serializer = ModifierGroupSerializer(
            self.menu.filling,
            data=self._body(
                self.menu.filling,
                [
                    self._row(self.menu.raspberry_filling, self.menu.raspberry_filling),
                    self._row(self.menu.mango_filling, None),
                ],
            ),
        )
        self.assertFalse(serializer.is_valid())

    def test_tech_card_lists_groups_by_descending_priority(self):
        self.menu.filling.priority = 1
        self.menu.filling.save(update_fields=["priority"])
        self.menu.decor.priority = 9
        self.menu.decor.save(update_fields=["priority"])
        user = User.objects.create_user("viewer", password="x")
        grant(user, "view_menu")
        client = APIClient()
        client.force_authenticate(user)
        response = client.get(f"/api/menu/tech-cards/{self.menu.cake.pk}/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            [group["group"] for group in response.json()["modifier_groups"]],
            [self.menu.decor.pk, self.menu.filling.pk],
        )


class OwnSectionBaseLineTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        self.client = APIClient()
        self.staff = User.objects.create_user("chef", password="x")
        grant(self.staff, "edit_menu")
        self.client.force_authenticate(self.staff)

    def _line(self, ingredient: Ingredient, quantity: str, unit: str) -> dict:
        return {
            "ingredient": ingredient.pk,
            "semi_product": None,
            "nested_tech_card": None,
            "quantity": quantity,
            "quantity_unit": unit,
            "loss_quantity": "0",
        }

    def _payload(self, lines: list[dict], sections: list[dict]) -> dict:
        return {
            "name": "Layer cake",
            "category": None,
            "kind": TechCard.KIND_WEIGHTED,
            "basis_weight_kg": "1",
            "basis_quantity": None,
            "method": "",
            "is_active": True,
            "lines": lines,
            "sections": sections,
            "modifier_groups": [],
            "modifier_lines": [],
        }

    def _chapter(self) -> dict:
        return {
            "name": "Глава_1",
            "method": "",
            "lines": [
                self._line(self.menu.flour, "100", UNIT_GRAM),
                self._line(self.menu.sugar, "200", UNIT_GRAM),
            ],
        }

    def _section_base_line(self, name: str) -> dict:
        return {
            "ingredient": None,
            "semi_product": None,
            "nested_tech_card": None,
            "nested_section_name": name,
            "quantity": None,
            "quantity_unit": UNIT_GRAM,
            "loss_quantity": "0",
        }

    def test_base_line_stores_the_gram_sum_and_counts_the_chapter_once(self):
        response = self.client.post(
            "/api/menu/tech-cards/",
            self._payload([self._section_base_line("Глава_1")], [self._chapter()]),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        line = body["lines"][0]
        self.assertEqual(line["name"], "Глава_1")
        self.assertEqual(line["nested_section"], body["sections"][0]["id"])
        self.assertEqual(Decimal(line["quantity"]), Decimal("300"))
        self.assertEqual(line["quantity_unit"], UNIT_GRAM)
        self.assertEqual(Decimal(line["loss_quantity"]), Decimal("0"))
        card = TechCard.objects.get(pk=body["id"])
        self.assertEqual(card.lines.get(section__isnull=True).nested_section.name, "Глава_1")
        needs = expand_order_item(card, Decimal("1"), 1, [], [])
        self.assertEqual(needs[self.menu.flour], Decimal("100"))
        self.assertEqual(needs[self.menu.sugar], Decimal("200"))
        self.assertEqual(stock_line_cost(card.lines.get(nested_section__isnull=False)), Decimal("2.00"))
        self.assertEqual(tech_card_cost(card, [], Decimal("1")), Decimal("2.00"))
        doubled = expand_order_item(card, Decimal("2"), 1, [], [])
        self.assertEqual(doubled[self.menu.flour], Decimal("200"))
        self.assertEqual(doubled[self.menu.sugar], Decimal("400"))

    def test_unreferenced_chapter_is_still_counted(self):
        response = self.client.post(
            "/api/menu/tech-cards/",
            self._payload([], [self._chapter()]),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        card = TechCard.objects.get(pk=response.json()["id"])
        needs = expand_order_item(card, Decimal("1"), 1, [], [])
        self.assertEqual(needs[self.menu.flour], Decimal("100"))
        self.assertEqual(needs[self.menu.sugar], Decimal("200"))

    def test_unknown_section_name_is_rejected(self):
        response = self.client.post(
            "/api/menu/tech-cards/",
            self._payload([self._section_base_line("Нет такой")], [self._chapter()]),
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("Unknown section", response.content.decode())

    def test_milliliters_and_pieces_do_not_change_the_shown_grams(self):
        section = self._chapter()
        section["lines"].extend(
            [
                self._line(self.menu.cream, "50", UNIT_MILLILITER),
                self._line(self.menu.paper, "2", UNIT_PIECE),
            ]
        )
        response = self.client.post(
            "/api/menu/tech-cards/",
            self._payload([self._section_base_line("Глава_1")], [section]),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(Decimal(body["lines"][0]["quantity"]), Decimal("300"))
        card = TechCard.objects.get(pk=body["id"])
        needs = expand_order_item(card, Decimal("1"), 1, [], [])
        self.assertEqual(needs[self.menu.cream], Decimal("50"))
        self.assertEqual(needs[self.menu.paper], Decimal("2"))


class CloneApiTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.menu = MenuFixture()
        self.client = APIClient()
        self.staff = User.objects.create_user("chef", password="x")
        grant(self.staff, "edit_menu")
        self.client.force_authenticate(self.staff)
        self.category = TechCardCategory.objects.create(name="Cakes")
        self.menu.cake.category = self.category
        self.menu.cake.method = "Bake."
        self.menu.cake.sale_price = Decimal("80.00")
        self.menu.cake.shelf_life_seconds = 172800
        self.menu.cake.storage_temperature = "+4"
        self.menu.cake.is_active = False
        self.menu.cake.save()
        self.section = TechCardSection.objects.create(
            tech_card=self.menu.cake,
            name="Syrup",
            method="Boil.",
            position=0,
        )
        TechCardLine.objects.create(
            tech_card=self.menu.cake,
            section=self.section,
            ingredient=self.menu.sugar,
            quantity=Decimal("100"),
            quantity_unit=UNIT_GRAM,
            position=0,
        )
        TechCardLine.objects.create(
            tech_card=self.menu.cake,
            nested_section=self.section,
            quantity=Decimal("100"),
            quantity_unit=UNIT_GRAM,
            loss_quantity=Decimal("0"),
            position=2,
        )
        TechCardLine.objects.create(
            tech_card=self.menu.cake,
            nested_tech_card=self.menu.bento,
            quantity=Decimal("1"),
            quantity_unit=UNIT_PIECE,
            position=3,
        )
        self.menu.extras.is_global = True
        self.menu.extras.save(update_fields=["is_global"])
        TechCardModifierGroup.objects.filter(tech_card=self.menu.cake, group=self.menu.filling).update(
            is_required=False
        )
        TechCardImage.objects.create(
            tech_card=self.menu.cake,
            image=SimpleUploadedFile("cake.png", b"cake-bytes", content_type="image/png"),
            position=0,
        )
        site_category = Category.objects.create(name="Shop", slug="shop")
        self.product = Product.objects.create(
            category=site_category,
            name="Site cake",
            slug="site-cake",
            base_price=Decimal("90.00"),
            tech_card=self.menu.cake,
        )
        semi_category = SemiProductCategory.objects.create(name="Bases")
        self.menu.sponge.category = semi_category
        self.menu.sponge.method = "Mix."
        self.menu.sponge.is_produced = True
        self.menu.sponge.avg_cost = Decimal("4.500000")
        self.menu.sponge.save()
        SemiProductImage.objects.create(
            semi_product=self.menu.sponge,
            image=SimpleUploadedFile("sponge.png", b"sponge-bytes", content_type="image/png"),
            position=0,
        )

    def test_clones_tech_card_without_site_products_or_global_groups(self):
        response = self.client.post(
            f"/api/menu/tech-cards/{self.menu.cake.pk}/clone/",
            {"name": "Cake copy"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        clone = TechCard.objects.get(pk=body["id"])
        self.assertNotEqual(clone.pk, self.menu.cake.pk)
        self.assertEqual(clone.name, "Cake copy")
        self.assertEqual(clone.category_id, self.category.pk)
        self.assertEqual(clone.kind, TechCard.KIND_WEIGHTED)
        self.assertEqual(clone.basis_weight_kg, Decimal("1"))
        self.assertEqual(clone.method, "Bake.")
        self.assertEqual(clone.sale_price, Decimal("80.00"))
        self.assertEqual(clone.shelf_life_seconds, 172800)
        self.assertEqual(clone.storage_temperature, "+4")
        self.assertFalse(clone.is_active)
        section = clone.sections.get()
        self.assertEqual(section.name, "Syrup")
        self.assertEqual(section.method, "Boil.")
        self.assertNotEqual(section.pk, self.section.pk)
        self.assertEqual(section.lines.get().ingredient_id, self.menu.sugar.pk)
        base = clone.lines.get(nested_section__isnull=False, section__isnull=True)
        self.assertEqual(base.nested_section_id, section.pk)
        nested = clone.lines.get(nested_tech_card__isnull=False)
        self.assertEqual(nested.nested_tech_card_id, self.menu.bento.pk)
        self.assertEqual(
            set(clone.modifier_groups.values_list("group_id", flat=True)),
            {self.menu.filling.pk, self.menu.decor.pk},
        )
        self.assertFalse(clone.modifier_groups.get(group=self.menu.filling).is_required)
        self.assertEqual(clone.modifier_lines.count(), self.menu.cake.modifier_lines.count())
        image = clone.images.get()
        self.assertNotEqual(image.image.name, self.menu.cake.images.get().image.name)
        self.assertEqual(image.image.read(), b"cake-bytes")
        self.assertEqual(list(clone.products.values_list("pk", flat=True)), [])
        self.assertEqual(self.product.tech_card_id, self.menu.cake.pk)

    def test_rejects_a_tech_card_name_that_is_taken_or_blank(self):
        taken = self.client.post(
            f"/api/menu/tech-cards/{self.menu.cake.pk}/clone/",
            {"name": self.menu.cake.name},
            format="json",
        )
        self.assertEqual(taken.status_code, 400, taken.content)
        self.assertIn("name", taken.json())
        self.assertEqual(TechCard.objects.filter(name=self.menu.cake.name).count(), 1)
        blank = self.client.post(
            f"/api/menu/tech-cards/{self.menu.cake.pk}/clone/",
            {"name": "  "},
            format="json",
        )
        self.assertEqual(blank.status_code, 400, blank.content)
        self.assertIn("name", blank.json())

    def test_clones_semi_product_lines_and_image_without_average_cost(self):
        response = self.client.post(
            f"/api/menu/semi-products/{self.menu.sponge.pk}/clone/",
            {"name": "Sponge copy"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        clone = SemiProduct.objects.get(pk=response.json()["id"])
        self.assertEqual(clone.name, "Sponge copy")
        self.assertEqual(clone.category_id, self.menu.sponge.category_id)
        self.assertEqual(clone.unit, self.menu.sponge.unit)
        self.assertEqual(clone.yield_quantity, self.menu.sponge.yield_quantity)
        self.assertTrue(clone.is_produced)
        self.assertEqual(clone.method, "Mix.")
        self.assertEqual(clone.avg_cost, Decimal("0"))
        self.assertEqual(
            list(clone.lines.values_list("ingredient_id", "quantity")),
            list(self.menu.sponge.lines.values_list("ingredient_id", "quantity")),
        )
        image = clone.images.get()
        self.assertNotEqual(image.image.name, self.menu.sponge.images.get().image.name)
        self.assertEqual(image.image.read(), b"sponge-bytes")
        taken = self.client.post(
            f"/api/menu/semi-products/{self.menu.sponge.pk}/clone/",
            {"name": "Sponge copy"},
            format="json",
        )
        self.assertEqual(taken.status_code, 400, taken.content)
        self.assertIn("name", taken.json())
