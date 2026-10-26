import importlib
from datetime import date
from decimal import Decimal

from django.apps import apps
from django.test import TestCase

_migration = importlib.import_module("crm.migrations.0068_link_historical_website_orders")
link_historical_website_orders = _migration.link_historical_website_orders
unlink_historical_website_orders = _migration.unlink_historical_website_orders
from crm.models import CrmOrder
from orders.models import Order


def _website(number: str) -> Order:
    return Order.objects.create(
        number=number,
        fulfillment_type=Order.FULFILLMENT_PICKUP,
        payment_method=Order.PAYMENT_CASH,
        customer_name="Site",
        customer_phone="555000000",
        customer_email=f"{number}@example.com",
    )


def _crm(**kwargs) -> CrmOrder:
    fields = {
        "date": date(2026, 7, 14),
        "contact": "Сайт",
        "nickname": "Сайт",
        "weight": "600",
        "filling": "Кб клубника",
        "cake_price": Decimal("65.00"),
    }
    fields.update(kwargs)
    return CrmOrder.objects.create(**fields)


class LinkHistoricalWebsiteOrdersTests(TestCase):
    def test_missing_rows_are_skipped(self):
        link_historical_website_orders(apps, None)
        unlink_historical_website_orders(apps, None)
        self.assertEqual(CrmOrder.objects.count(), 0)

    def test_links_pair_without_changing_price(self):
        website = _website("73175")
        crm = _crm(id=1000126, cake_price=Decimal("65.00"), filling="Кб клубника")
        link_historical_website_orders(apps, None)
        crm.refresh_from_db()
        self.assertEqual(crm.website_order_id, website.pk)
        self.assertEqual(crm.cake_price, Decimal("65.00"))
        self.assertEqual(crm.filling, "Кб клубника")
        self.assertEqual(crm.nickname, "Сайт")

    def test_skips_deleted_crm_order(self):
        _website("73020")
        crm = _crm(id=1000016, deleted=True, cake_price=Decimal("0.00"))
        link_historical_website_orders(apps, None)
        crm.refresh_from_db()
        self.assertIsNone(crm.website_order_id)

    def test_skips_when_website_order_is_already_taken(self):
        website = _website("73020")
        other = _crm(website_order=website)
        target = _crm(id=1000016, cake_price=Decimal("0.00"))
        link_historical_website_orders(apps, None)
        target.refresh_from_db()
        other.refresh_from_db()
        self.assertIsNone(target.website_order_id)
        self.assertEqual(other.website_order_id, website.pk)

    def test_skips_crm_order_that_already_has_a_website_order(self):
        _website("73020")
        existing = _website("73037")
        crm = _crm(id=1000016, website_order=existing, cake_price=Decimal("0.00"))
        link_historical_website_orders(apps, None)
        crm.refresh_from_db()
        self.assertEqual(crm.website_order_id, existing.pk)

    def test_unlink_clears_only_the_paired_order(self):
        website = _website("73243")
        crm = _crm(id=26, website_order=website)
        unrelated_site = _website("73999")
        unrelated = _crm(id=77, website_order=unrelated_site)
        moved_site = _website("73998")
        moved = _crm(id=1000126, website_order=moved_site)
        unlink_historical_website_orders(apps, None)
        crm.refresh_from_db()
        unrelated.refresh_from_db()
        moved.refresh_from_db()
        self.assertIsNone(crm.website_order_id)
        self.assertEqual(unrelated.website_order_id, unrelated_site.pk)
        self.assertEqual(moved.website_order_id, moved_site.pk)
