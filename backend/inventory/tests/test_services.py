from datetime import date
from decimal import Decimal

from django.test import TestCase

from crm.models import CrmOrder
from inventory.models import (
    InventoryCount,
    InventoryCountLine,
    Production,
    StockMovement,
    Supply,
    SupplyLine,
)
from inventory.services import (
    apply_production,
    apply_supply,
    close_inventory_count,
    delete_document,
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
