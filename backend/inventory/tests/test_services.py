from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from crm.models import CrmOrder, CrmOrderItemLine
from inventory.models import (
    FinishedGood,
    FinishedProduction,
    FinishedProductionLine,
    InventoryCount,
    InventoryCountLine,
    Production,
    StockMovement,
    Supply,
    SupplyLine,
    WriteOff,
    WriteOffLine,
    WriteOffReason,
)
from inventory.serializers import FinishedProductionSerializer
from inventory.services import (
    apply_finished_production,
    apply_production,
    apply_supply,
    apply_write_off,
    close_inventory_count,
    delete_document,
    ensure_finished_good,
    stock_levels,
    stock_of,
    sync_order_write_off,
)
from menu.tests.fixtures import MenuFixture, add_item, make_crm_order


def supply(ingredient, quantity: str, total: str, on: date) -> Supply:
    document = Supply.objects.create(date=on)
    SupplyLine.objects.create(supply=document, ingredient=ingredient, quantity=Decimal(quantity), total=Decimal(total))
    apply_supply(document)
    return document


def stock(component) -> Decimal:
    return stock_of(component, stock_levels(None, None))


class SupplyTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()

    def test_weighted_average_cost_after_several_supplies(self):
        flour = self.menu.flour
        supply(flour, "1000", "10.00", date(2026, 10, 1))
        flour.refresh_from_db()
        self.assertEqual(flour.avg_cost, Decimal("0.01"))
        supply(flour, "1000", "20.00", date(2026, 10, 2))
        flour.refresh_from_db()
        self.assertEqual(flour.avg_cost, Decimal("0.015"))
        self.assertEqual(stock(flour), Decimal("2000"))

    def test_editing_supply_replays_average_cost(self):
        flour = self.menu.flour
        first = supply(flour, "1000", "10.00", date(2026, 10, 1))
        supply(flour, "1000", "20.00", date(2026, 10, 2))
        first.lines.update(total=Decimal("30.00"))
        apply_supply(first)
        flour.refresh_from_db()
        self.assertEqual(flour.avg_cost, Decimal("0.025"))

    def test_deleting_supply_removes_stock(self):
        flour = self.menu.flour
        document = supply(flour, "1000", "10.00", date(2026, 10, 1))
        delete_document(document)
        self.assertEqual(stock(flour), Decimal("0"))


class ProductionTests(TestCase):
    def test_production_consumes_components_and_sets_cost(self):
        menu = MenuFixture()
        supply(menu.flour, "5000", "50.00", date(2026, 10, 1))
        supply(menu.sugar, "5000", "25.00", date(2026, 10, 1))
        production = Production.objects.create(
            date=date(2026, 10, 2),
            semi_product=menu.frozen_sponge,
            quantity=Decimal("2000"),
        )
        apply_production(production)
        menu.frozen_sponge.refresh_from_db()
        self.assertEqual(stock(menu.flour), Decimal("3800"))
        self.assertEqual(stock(menu.sugar), Decimal("4200"))
        self.assertEqual(stock(menu.frozen_sponge), Decimal("2000"))
        self.assertEqual(menu.frozen_sponge.avg_cost, Decimal("0.008"))


class OrderWriteOffTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        supply(self.menu.flour, "1000", "10.00", date(2026, 10, 1))
        self.order = make_crm_order(CrmOrder.STATUS_NEW)
        self.item = add_item(self.order, self.menu.bento, None, 1, [])

    def _set_status(self, status: str) -> None:
        self.order.status = status
        self.order.save()
        sync_order_write_off(self.order)

    def test_new_order_does_not_write_off(self):
        sync_order_write_off(self.order)
        self.assertFalse(StockMovement.objects.filter(crm_order=self.order).exists())

    def test_ready_writes_off_and_rollback_restores(self):
        self._set_status(CrmOrder.STATUS_READY)
        self.assertEqual(stock(self.menu.flour), Decimal("900"))
        movement = StockMovement.objects.get(crm_order=self.order)
        self.assertEqual(movement.unit_cost, Decimal("0.01"))
        self._set_status(CrmOrder.STATUS_IN_WORK)
        self.assertEqual(stock(self.menu.flour), Decimal("1000"))

    def test_later_statuses_keep_write_off(self):
        for status in [
            CrmOrder.STATUS_READY,
            CrmOrder.STATUS_CLIENT_APPROVED,
            CrmOrder.STATUS_IN_DELIVERY,
            CrmOrder.STATUS_DELIVERED,
        ]:
            self._set_status(status)
            self.assertEqual(stock(self.menu.flour), Decimal("900"))

    def test_deleted_order_restores_stock(self):
        self._set_status(CrmOrder.STATUS_READY)
        self.order.deleted = True
        self.order.save()
        sync_order_write_off(self.order)
        self.assertEqual(stock(self.menu.flour), Decimal("1000"))

    def test_editing_items_rewrites_movements(self):
        self._set_status(CrmOrder.STATUS_READY)
        self.item.quantity = 3
        self.item.save()
        sync_order_write_off(self.order)
        self.assertEqual(stock(self.menu.flour), Decimal("700"))
        self.assertEqual(StockMovement.objects.filter(crm_order=self.order).count(), 1)

    def test_negative_stock_is_allowed(self):
        self.item.quantity = 20
        self.item.save()
        self._set_status(CrmOrder.STATUS_READY)
        self.assertEqual(stock(self.menu.flour), Decimal("-1000"))


class ManualCostWithoutSupplyTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        self.order = make_crm_order(CrmOrder.STATUS_NEW)
        add_item(self.order, self.menu.bento, None, 1, [])

    def test_order_write_off_keeps_manual_cost(self):
        self.order.status = CrmOrder.STATUS_READY
        self.order.save()
        sync_order_write_off(self.order)
        self.menu.flour.refresh_from_db()
        self.assertEqual(self.menu.flour.avg_cost, Decimal("0.01"))
        movement = StockMovement.objects.get(crm_order=self.order)
        self.assertEqual(movement.unit_cost, Decimal("0.01"))

    def test_other_supply_keeps_manual_cost(self):
        self.order.status = CrmOrder.STATUS_READY
        self.order.save()
        sync_order_write_off(self.order)
        supply(self.menu.sugar, "1000", "10.00", date(2026, 10, 21))
        self.menu.flour.refresh_from_db()
        self.assertEqual(self.menu.flour.avg_cost, Decimal("0.01"))


class InventoryCountTests(TestCase):
    def test_closing_count_adjusts_stock_to_actual(self):
        menu = MenuFixture()
        supply(menu.flour, "1000", "10.00", date(2026, 10, 1))
        count = InventoryCount.objects.create(date=date(2026, 10, 5))
        line = InventoryCountLine.objects.create(count=count, ingredient=menu.flour, actual_quantity=Decimal("900"))
        InventoryCountLine.objects.create(
            count=count,
            ingredient=menu.cream,
            actual_quantity=Decimal("500"),
            unit_cost=Decimal("0.04"),
        )
        close_inventory_count(count)
        count.refresh_from_db()
        line.refresh_from_db()
        self.assertEqual(count.status, InventoryCount.STATUS_CLOSED)
        self.assertIsNotNone(count.closed_at)
        self.assertEqual(line.expected_quantity, Decimal("1000"))
        self.assertEqual(stock(menu.flour), Decimal("900"))
        self.assertEqual(stock(menu.cream), Decimal("500"))
        menu.flour.refresh_from_db()
        menu.cream.refresh_from_db()
        self.assertEqual(menu.flour.avg_cost, Decimal("0.01"))
        self.assertEqual(menu.cream.avg_cost, Decimal("0.04"))

    def test_count_uses_stock_on_its_date(self):
        menu = MenuFixture()
        supply(menu.flour, "1000", "10.00", date(2026, 10, 1))
        supply(menu.flour, "500", "5.00", date(2026, 10, 10))
        count = InventoryCount.objects.create(date=date(2026, 10, 5))
        line = InventoryCountLine.objects.create(count=count, ingredient=menu.flour, actual_quantity=Decimal("1000"))
        close_inventory_count(count)
        line.refresh_from_db()
        self.assertEqual(line.expected_quantity, Decimal("1000"))
        self.assertEqual(stock(menu.flour), Decimal("1500"))


def produce_finished(tech_card, weight, modifiers, quantity: int, on: date):
    good = ensure_finished_good(tech_card, weight, modifiers)
    document = FinishedProduction.objects.create(date=on, comment="")
    FinishedProductionLine.objects.create(production=document, finished_good=good, quantity=quantity)
    apply_finished_production(document)
    good.refresh_from_db()
    return document, good


class FinishedGoodTests(TestCase):
    def test_piece_production_consumes_recipe_and_stocks_pieces(self):
        menu = MenuFixture()
        supply(menu.flour, "1000", "10.00", date(2026, 10, 1))
        document, good = produce_finished(menu.bento, None, [], 2, date(2026, 10, 2))
        self.assertEqual(stock(menu.flour), Decimal("800"))
        self.assertEqual(stock(good), Decimal("2"))
        self.assertEqual(good.avg_cost, Decimal("1"))
        self.assertEqual(document.lines.get().finished_good, good)

    def test_weighted_production_stocks_pieces_of_that_weight(self):
        menu = MenuFixture()
        supply(menu.flour, "5000", "50.00", date(2026, 10, 1))
        _, good = produce_finished(
            menu.cake,
            Decimal("1.200"),
            [(menu.raspberry_filling, 1)],
            1,
            date(2026, 10, 2),
        )
        self.assertEqual(stock(good), Decimal("1"))
        self.assertEqual(good.weight_kg, Decimal("1.200"))
        self.assertEqual(good.avg_cost, Decimal("15.6"))
        self.assertIn("1.200 kg", good.name)
        self.assertIn(menu.raspberry_filling.name, good.name)

    def test_second_production_of_the_same_assembly_averages_cost(self):
        menu = MenuFixture()
        supply(menu.flour, "1000", "10.00", date(2026, 10, 1))
        _, good = produce_finished(menu.bento, None, [], 2, date(2026, 10, 2))
        supply(menu.flour, "200", "4.00", date(2026, 10, 3))
        produce_finished(menu.bento, None, [], 2, date(2026, 10, 4))
        good.refresh_from_db()
        self.assertEqual(FinishedGood.objects.count(), 1)
        self.assertEqual(stock(good), Decimal("4"))
        self.assertEqual(good.avg_cost, Decimal("1.1"))

    def test_exact_sale_writes_off_pieces(self):
        menu = MenuFixture()
        supply(menu.flour, "1000", "10.00", date(2026, 10, 1))
        _, good = produce_finished(menu.bento, None, [], 2, date(2026, 10, 2))
        order = make_crm_order(CrmOrder.STATUS_READY)
        add_item(order, menu.bento, None, 1, [])
        sync_order_write_off(order)
        self.assertEqual(stock(good), Decimal("1"))
        self.assertEqual(stock(menu.flour), Decimal("800"))
        self.assertEqual(StockMovement.objects.filter(crm_order=order, finished_good=good).count(), 1)

    def test_sale_of_more_pieces_than_produced_goes_negative(self):
        menu = MenuFixture()
        supply(menu.flour, "1000", "10.00", date(2026, 10, 1))
        _, good = produce_finished(menu.bento, None, [], 1, date(2026, 10, 2))
        order = make_crm_order(CrmOrder.STATUS_READY)
        add_item(order, menu.bento, None, 3, [])
        sync_order_write_off(order)
        self.assertEqual(stock(good), Decimal("-2"))
        self.assertEqual(stock(menu.flour), Decimal("900"))

    def test_different_weight_writes_off_ingredients(self):
        menu = MenuFixture()
        supply(menu.flour, "5000", "50.00", date(2026, 10, 1))
        _, good = produce_finished(
            menu.cake,
            Decimal("1.200"),
            [(menu.raspberry_filling, 1)],
            1,
            date(2026, 10, 2),
        )
        flour_after = stock(menu.flour)
        order = make_crm_order(CrmOrder.STATUS_READY)
        add_item(order, menu.cake, Decimal("1.500"), 1, [(menu.raspberry_filling, 1)])
        sync_order_write_off(order)
        self.assertEqual(stock(good), Decimal("1"))
        self.assertLess(stock(menu.flour), flour_after)

    def test_different_modifier_writes_off_ingredients(self):
        menu = MenuFixture()
        supply(menu.flour, "5000", "50.00", date(2026, 10, 1))
        _, good = produce_finished(
            menu.cake,
            Decimal("1"),
            [(menu.raspberry_filling, 1)],
            1,
            date(2026, 10, 2),
        )
        flour_after = stock(menu.flour)
        order = make_crm_order(CrmOrder.STATUS_READY)
        add_item(order, menu.cake, Decimal("1"), 1, [(menu.berries, 1)])
        sync_order_write_off(order)
        self.assertEqual(stock(good), Decimal("1"))
        self.assertLess(stock(menu.flour), flour_after)

    def test_matching_sale_still_writes_off_extra_lines(self):
        menu = MenuFixture()
        supply(menu.flour, "1000", "10.00", date(2026, 10, 1))
        _, good = produce_finished(menu.bento, None, [], 1, date(2026, 10, 2))
        order = make_crm_order(CrmOrder.STATUS_READY)
        item = add_item(order, menu.bento, None, 1, [])
        CrmOrderItemLine.objects.create(item=item, ingredient=menu.raspberry, quantity=Decimal("10"))
        sync_order_write_off(order)
        self.assertEqual(stock(good), Decimal("0"))
        self.assertEqual(stock(menu.flour), Decimal("900"))
        self.assertEqual(stock(menu.raspberry), Decimal("-10"))

    def test_deleting_the_only_production_restores_ingredient_write_off(self):
        menu = MenuFixture()
        supply(menu.flour, "1000", "10.00", date(2026, 10, 1))
        document, good = produce_finished(menu.bento, None, [], 2, date(2026, 10, 2))
        delete_document(document)
        self.assertFalse(FinishedGood.objects.filter(pk=good.pk).exists())
        order = make_crm_order(CrmOrder.STATUS_READY)
        add_item(order, menu.bento, None, 1, [])
        sync_order_write_off(order)
        self.assertEqual(stock(menu.flour), Decimal("900"))
        self.assertFalse(StockMovement.objects.filter(crm_order=order, finished_good__isnull=False).exists())

    def test_write_off_removes_pieces(self):
        menu = MenuFixture()
        supply(menu.flour, "1000", "10.00", date(2026, 10, 1))
        _, good = produce_finished(menu.bento, None, [], 2, date(2026, 10, 2))
        reason = WriteOffReason.objects.create(name="Spoiled")
        write_off = WriteOff.objects.create(date=date(2026, 10, 3), reason=reason, comment="")
        WriteOffLine.objects.create(write_off=write_off, finished_good=good, quantity=Decimal("1"))
        apply_write_off(write_off)
        self.assertEqual(stock(good), Decimal("1"))
        self.assertEqual(stock(menu.flour), Decimal("800"))

    def test_inventory_count_sets_piece_stock(self):
        menu = MenuFixture()
        supply(menu.flour, "1000", "10.00", date(2026, 10, 1))
        _, good = produce_finished(menu.bento, None, [], 2, date(2026, 10, 2))
        count = InventoryCount.objects.create(date=date(2026, 10, 5), comment="")
        InventoryCountLine.objects.create(count=count, finished_good=good, actual_quantity=Decimal("5"))
        close_inventory_count(count)
        self.assertEqual(stock(good), Decimal("5"))

    def test_inventory_count_rejects_a_fraction_of_a_piece(self):
        menu = MenuFixture()
        supply(menu.flour, "1000", "10.00", date(2026, 10, 1))
        _, good = produce_finished(menu.bento, None, [], 2, date(2026, 10, 2))
        count = InventoryCount.objects.create(date=date(2026, 10, 5), comment="")
        InventoryCountLine.objects.create(count=count, finished_good=good, actual_quantity=Decimal("1.5"))
        with self.assertRaises(ValidationError):
            close_inventory_count(count)

    def test_required_modifier_and_piece_weight_are_rejected(self):
        menu = MenuFixture()
        with self.assertRaises(ValidationError):
            ensure_finished_good(menu.cake, Decimal("1"), [])
        with self.assertRaises(ValidationError):
            ensure_finished_good(menu.bento, Decimal("1"), [])

    def test_duplicate_assembly_in_one_document_is_rejected(self):
        menu = MenuFixture()
        payload = {
            "date": "2026-10-02",
            "comment": "",
            "lines": [
                {"tech_card": menu.bento.pk, "weight_kg": None, "modifiers": [], "quantity": 1},
                {"tech_card": menu.bento.pk, "weight_kg": None, "modifiers": [], "quantity": 2},
            ],
        }
        serializer = FinishedProductionSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
