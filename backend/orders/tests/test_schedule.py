from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase
from rest_framework import serializers

from cart.models import Cart, CartItem
from catalog.models import Category, Product
from orders.schedule import build_fulfillment_options, resolve_schedule_selection

_TB = ZoneInfo("Asia/Tbilisi")


class ScheduleRulesTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Cat", slug="cat", position=0)
        self.prod_same = Product.objects.create(
            category=self.cat,
            name="Same",
            slug="same-p",
            description="",
            base_price=Decimal("10.00"),
            delivery_schedule_tier=Product.DELIVERY_SCHEDULE_SAME_DAY,
        )
        self.prod_p2 = Product.objects.create(
            category=self.cat,
            name="Late",
            slug="late-p",
            description="",
            base_price=Decimal("10.00"),
            delivery_schedule_tier=Product.DELIVERY_SCHEDULE_PLUS_2,
        )
        self.cart = Cart.objects.create()

    def _add_item(self, product: Product) -> None:
        CartItem.objects.create(cart=self.cart, product=product, quantity=1)

    @staticmethod
    def _frozen_now(y: int, mo: int, d: int, hh: int, mm: int = 0) -> datetime:
        return datetime(y, mo, d, hh, mm, tzinfo=_TB)

    @patch("django.utils.timezone.now")
    def test_same_day_before_cutoff_express_and_today(self, mock_now):
        mock_now.return_value = self._frozen_now(2026, 5, 21, 11, 30)
        self._add_item(self.prod_same)
        opts = build_fulfillment_options(self.cart)
        self.assertTrue(opts["express_available"])
        self.assertEqual(opts["timezone"], "Asia/Tbilisi")
        self.assertEqual(opts["dates"][0]["date"], "2026-05-21")

    @patch("django.utils.timezone.now")
    def test_before_work_hours_no_express_slots_from_open(self, mock_now):
        mock_now.return_value = self._frozen_now(2026, 5, 21, 10, 30)
        self._add_item(self.prod_same)
        opts = build_fulfillment_options(self.cart)
        self.assertFalse(opts["express_available"])
        self.assertEqual(opts["dates"][0]["date"], "2026-05-21")
        today_slots = opts["dates"][0]["slots"]
        self.assertEqual(today_slots[0]["start_time"], "11:00")

    @patch("django.utils.timezone.now")
    def test_scheduled_slots_on_today_skip_next_two_hours(self, mock_now):
        mock_now.return_value = self._frozen_now(2026, 5, 21, 11, 0)
        self._add_item(self.prod_same)
        opts = build_fulfillment_options(self.cart)
        today_slots = opts["dates"][0]["slots"]
        self.assertFalse(any(s["start_time"] == "11:00" for s in today_slots))
        self.assertFalse(any(s["start_time"] == "12:00" for s in today_slots))
        self.assertTrue(any(s["start_time"] == "13:00" for s in today_slots))

    @patch("django.utils.timezone.now")
    def test_same_day_after_cutoff_no_express_min_tomorrow(self, mock_now):
        mock_now.return_value = self._frozen_now(2026, 5, 21, 16, 0)
        self._add_item(self.prod_same)
        opts = build_fulfillment_options(self.cart)
        self.assertFalse(opts["express_available"])
        self.assertEqual(opts["dates"][0]["date"], "2026-05-22")

    @patch("django.utils.timezone.now")
    def test_plus_2_starts_two_days_out(self, mock_now):
        mock_now.return_value = self._frozen_now(2026, 5, 21, 10, 0)
        self._add_item(self.prod_p2)
        opts = build_fulfillment_options(self.cart)
        self.assertFalse(opts["express_available"])
        self.assertEqual(opts["dates"][0]["date"], "2026-05-23")

    @patch("django.utils.timezone.now")
    def test_mixed_cart_uses_strictest_tier(self, mock_now):
        mock_now.return_value = self._frozen_now(2026, 5, 21, 10, 0)
        self._add_item(self.prod_same)
        self._add_item(self.prod_p2)
        opts = build_fulfillment_options(self.cart)
        self.assertEqual(opts["dates"][0]["date"], "2026-05-23")

    @patch("django.utils.timezone.now")
    def test_express_rejected_after_cutoff(self, mock_now):
        mock_now.return_value = self._frozen_now(2026, 5, 21, 16, 0)
        self._add_item(self.prod_same)
        with self.assertRaises(serializers.ValidationError):
            resolve_schedule_selection(self.cart, "express", None, None, None)

    @patch("django.utils.timezone.now")
    def test_invalid_slot_rejected(self, mock_now):
        mock_now.return_value = self._frozen_now(2026, 5, 21, 10, 0)
        self._add_item(self.prod_same)
        with self.assertRaises(serializers.ValidationError):
            resolve_schedule_selection(
                self.cart,
                "slot",
                date(2026, 5, 21),
                time(9, 0),
                time(10, 0),
            )

    @patch("django.utils.timezone.now")
    def test_valid_slot_resolves(self, mock_now):
        mock_now.return_value = self._frozen_now(2026, 5, 21, 10, 0)
        self._add_item(self.prod_same)
        opts = build_fulfillment_options(self.cart)
        first = opts["dates"][0]["slots"][0]
        st = time.fromisoformat(first["start_time"])
        et = time.fromisoformat(first["end_time"])
        d = date.fromisoformat(opts["dates"][0]["date"])
        s, e = resolve_schedule_selection(self.cart, "slot", d, st, et)
        self.assertIsNotNone(s.tzinfo)
        self.assertIsNotNone(e.tzinfo)

    @patch("django.utils.timezone.now")
    def test_product_inherits_tier_from_category(self, mock_now):
        mock_now.return_value = self._frozen_now(2026, 5, 21, 10, 0)
        self.cat.delivery_schedule_tier = Product.DELIVERY_SCHEDULE_PLUS_2
        self.cat.save()
        inherited = Product.objects.create(
            category=self.cat,
            name="Inherited",
            slug="inherited-p",
            description="",
            base_price=Decimal("10.00"),
        )
        self._add_item(inherited)
        opts = build_fulfillment_options(self.cart)
        self.assertEqual(opts["dates"][0]["date"], "2026-05-23")

    @patch("django.utils.timezone.now")
    def test_product_override_beats_category(self, mock_now):
        mock_now.return_value = self._frozen_now(2026, 5, 21, 10, 0)
        self.cat.delivery_schedule_tier = Product.DELIVERY_SCHEDULE_SAME_DAY
        self.cat.save()
        overridden = Product.objects.create(
            category=self.cat,
            name="Override",
            slug="override-p",
            description="",
            base_price=Decimal("10.00"),
            delivery_schedule_tier=Product.DELIVERY_SCHEDULE_PLUS_3,
        )
        self._add_item(overridden)
        opts = build_fulfillment_options(self.cart)
        self.assertEqual(opts["dates"][0]["date"], "2026-05-24")
