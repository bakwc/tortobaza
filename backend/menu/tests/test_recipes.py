from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from crm.models import CrmOrder, CrmOrderItemLine
from menu.models import (
    UNIT_GRAM,
    UNIT_MILLILITER,
    Ingredient,
    SemiProduct,
    SemiProductLine,
    TechCardLine,
    TechCardSection,
)
from menu.serializers import RecipeLineSerializer
from menu.recipes import (
    component_quantity,
    expand_order,
    expand_order_item,
    expand_semi_product,
    order_cost,
    tech_card_cost,
    validate_order_item,
)
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

    def test_loss_percent_increases_gross_quantity(self):
        TechCardLine.objects.filter(tech_card=self.menu.bento).update(loss_percent=Decimal("20"))
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
            loss_percent=Decimal("20"),
        )
        needs = expand_order_item(self.menu.cake, Decimal("1"), 1, [], [])
        self.assertEqual(needs[self.menu.cream], Decimal("62.5"))

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
                "loss_percent": "0",
                "quantity_unit": UNIT_MILLILITER,
            }
        )
        self.assertFalse(serializer.is_valid())
