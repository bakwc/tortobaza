import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.test import TestCase

from crm.liberty_online_links import sync_liberty_online_order_links
from crm.liberty_statement import ONLINE_PREFIX
from crm.models import CrmOrder, FinancialAccount, FinancialTransaction
from orders.models import LibertyPayment, Order

_TB = ZoneInfo("Asia/Tbilisi")


def _at(year: int, month: int, day: int, hour: int, minute: int, second: int) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=_TB)


def _website(total: Decimal) -> Order:
    return Order.objects.create(
        fulfillment_type=Order.FULFILLMENT_PICKUP,
        payment_method=Order.PAYMENT_CARD,
        payment_status=Order.PAYMENT_PAID,
        customer_name="Customer",
        customer_phone="+995555000000",
        customer_email="customer@example.com",
        total=total,
    )


def _crm(website: Order, **kwargs) -> CrmOrder:
    fields = {
        "date": date(2026, 9, 20),
        "contact": "Customer",
        "weight": "1kg",
        "filling": "Vanilla",
        "cake_price": website.total,
        "is_paid": True,
        "payment_type": CrmOrder.PAYMENT_ONLINE,
        "website_order": website,
        "fulfillment_type": CrmOrder.FULFILLMENT_PICKUP,
        "delivery_address": "",
    }
    fields.update(kwargs)
    return CrmOrder.objects.create(**fields)


def _payment(
    order: Order,
    gross: Decimal,
    created: datetime,
    updated: datetime,
    **kwargs,
) -> LibertyPayment:
    fields = {
        "order": order,
        "ordercode": uuid.uuid4().hex,
        "amount_tetri": int(gross * 100),
        "status": LibertyPayment.STATUS_COMPLETED,
        "testmode": False,
    }
    fields.update(kwargs)
    payment = LibertyPayment.objects.create(**fields)
    LibertyPayment.objects.filter(pk=payment.pk).update(created_at=created, updated_at=updated)
    return payment


def _account() -> FinancialAccount:
    return FinancialAccount.objects.create(name="Liberty", kind=FinancialAccount.KIND_BANK)


def _description(authorized: datetime, gross: Decimal) -> str:
    return (
        f"{ONLINE_PREFIX} ანგარიშსწორება: ORDERID 1,  Georgia "
        f"{authorized:%d/%m/%Y %H:%M:%S} | AUTH. No 1 | GEL {gross:.2f} - 9001166"
    )


def _online(net: Decimal, authorized: datetime, bank_date: date, gross: Decimal) -> FinancialTransaction:
    return FinancialTransaction.objects.create(
        account=_account(),
        date=bank_date,
        amount=net,
        kind=FinancialTransaction.KIND_INCOME,
        income_type=FinancialTransaction.INCOME_ONLINE,
        description=_description(authorized, gross),
    )


def _around(authorized: datetime) -> tuple[datetime, datetime]:
    return authorized - timedelta(seconds=30), authorized + timedelta(seconds=20)


class SyncLibertyOnlineOrderLinksTests(TestCase):
    def test_links_two_percent(self):
        authorized = _at(2026, 9, 10, 22, 9, 36)
        created, updated = _around(authorized)
        website = _website(Decimal("65.00"))
        order = _crm(website, date=date(2026, 9, 11))
        _payment(website, Decimal("65.00"), created, updated)
        transaction = _online(Decimal("63.70"), authorized, date(2026, 9, 11), Decimal("65.00"))

        sync_liberty_online_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_links_one_point_seven_percent(self):
        cases = [
            (Decimal("112.00"), Decimal("110.10"), _at(2026, 9, 11, 10, 45, 20), date(2026, 9, 14)),
            (Decimal("195.00"), Decimal("191.68"), _at(2026, 9, 15, 14, 17, 47), date(2026, 9, 16)),
            (Decimal("90.00"), Decimal("88.47"), _at(2026, 9, 19, 12, 50, 47), date(2026, 9, 21)),
            (Decimal("75.00"), Decimal("73.72"), _at(2026, 9, 17, 19, 10, 8), date(2026, 9, 18)),
        ]
        expected = []
        for gross, net, authorized, bank_date in cases:
            created, updated = _around(authorized)
            website = _website(gross)
            order = _crm(website)
            _payment(website, gross, created, updated)
            transaction = _online(net, authorized, bank_date, gross)
            expected.append((transaction, order))

        sync_liberty_online_order_links()

        for transaction, order in expected:
            self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_links_same_gross_on_different_days(self):
        first_authorized = _at(2026, 9, 17, 19, 10, 8)
        second_authorized = _at(2026, 9, 20, 16, 59, 1)
        first_created, first_updated = _around(first_authorized)
        second_created, second_updated = _around(second_authorized)
        first_website = _website(Decimal("75.00"))
        second_website = _website(Decimal("75.00"))
        first_order = _crm(first_website, date=date(2026, 9, 18))
        second_order = _crm(second_website, date=date(2026, 9, 21))
        _payment(first_website, Decimal("75.00"), first_created, first_updated)
        _payment(second_website, Decimal("75.00"), second_created, second_updated)
        first_tx = _online(Decimal("73.72"), first_authorized, date(2026, 9, 18), Decimal("75.00"))
        second_tx = _online(Decimal("73.50"), second_authorized, date(2026, 9, 21), Decimal("75.00"))

        sync_liberty_online_order_links()

        self.assertEqual(first_tx.crm_orders.get().pk, first_order.pk)
        self.assertEqual(second_tx.crm_orders.get().pk, second_order.pk)

    def test_links_when_bank_date_is_not_the_next_day(self):
        friday = _at(2026, 9, 11, 10, 45, 20)
        saturday = _at(2026, 9, 19, 12, 50, 47)
        friday_created, friday_updated = _around(friday)
        saturday_created, saturday_updated = _around(saturday)
        friday_website = _website(Decimal("112.00"))
        saturday_website = _website(Decimal("90.00"))
        friday_order = _crm(friday_website)
        saturday_order = _crm(saturday_website)
        _payment(friday_website, Decimal("112.00"), friday_created, friday_updated)
        _payment(saturday_website, Decimal("90.00"), saturday_created, saturday_updated)
        friday_tx = _online(Decimal("110.10"), friday, date(2026, 9, 14), Decimal("112.00"))
        saturday_tx = _online(Decimal("88.47"), saturday, date(2026, 9, 21), Decimal("90.00"))

        sync_liberty_online_order_links()

        self.assertEqual(friday_tx.crm_orders.get().pk, friday_order.pk)
        self.assertEqual(saturday_tx.crm_orders.get().pk, saturday_order.pk)

    def test_links_when_callback_is_late(self):
        authorized = _at(2026, 7, 8, 22, 44, 54)
        website = _website(Decimal("9.00"))
        order = _crm(website)
        _payment(
            website,
            Decimal("9.00"),
            _at(2026, 7, 8, 22, 42, 45),
            _at(2026, 7, 8, 22, 57, 29),
        )
        transaction = _online(Decimal("8.82"), authorized, date(2026, 7, 9), Decimal("9.00"))

        sync_liberty_online_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_links_three_equal_amounts_the_same_evening(self):
        slots = [
            (_at(2026, 7, 8, 22, 44, 54), _at(2026, 7, 8, 22, 42, 45), _at(2026, 7, 8, 22, 57, 29)),
            (_at(2026, 7, 8, 23, 3, 35), _at(2026, 7, 8, 23, 2, 9), _at(2026, 7, 8, 23, 3, 56)),
            (_at(2026, 7, 9, 0, 36, 41), _at(2026, 7, 9, 0, 35, 31), _at(2026, 7, 9, 0, 36, 57)),
        ]
        expected = []
        for authorized, created, updated in slots:
            website = _website(Decimal("9.00"))
            order = _crm(website)
            _payment(website, Decimal("9.00"), created, updated)
            transaction = _online(Decimal("8.82"), authorized, date(2026, 7, 9), Decimal("9.00"))
            expected.append((transaction, order))

        sync_liberty_online_order_links()

        for transaction, order in expected:
            self.assertEqual(transaction.crm_orders.get().pk, order.pk)

    def test_skips_completed_payment_without_crm_order(self):
        authorized = _at(2026, 7, 8, 22, 44, 54)
        website = _website(Decimal("9.00"))
        _payment(
            website,
            Decimal("9.00"),
            _at(2026, 7, 8, 22, 42, 45),
            _at(2026, 7, 8, 22, 57, 29),
        )
        transaction = _online(Decimal("8.82"), authorized, date(2026, 7, 9), Decimal("9.00"))

        sync_liberty_online_order_links()

        self.assertEqual(transaction.crm_orders.count(), 0)

    def test_skips_when_two_payments_contain_the_authorization(self):
        authorized = _at(2026, 9, 6, 12, 0, 0)
        created = _at(2026, 9, 6, 11, 0, 0)
        updated = _at(2026, 9, 6, 13, 0, 0)
        first = _website(Decimal("100.00"))
        second = _website(Decimal("100.00"))
        _crm(first)
        _crm(second)
        _payment(first, Decimal("100.00"), created, updated)
        _payment(second, Decimal("100.00"), created, updated)
        transaction = _online(Decimal("98.00"), authorized, date(2026, 9, 7), Decimal("100.00"))

        sync_liberty_online_order_links()

        self.assertEqual(transaction.crm_orders.count(), 0)

    def test_skips_when_commission_is_above_ten_percent(self):
        authorized = _at(2026, 9, 6, 12, 0, 0)
        created, updated = _around(authorized)
        website = _website(Decimal("100.00"))
        _crm(website)
        _payment(website, Decimal("100.00"), created, updated)
        transaction = _online(Decimal("89.00"), authorized, date(2026, 9, 7), Decimal("100.00"))

        sync_liberty_online_order_links()

        self.assertEqual(transaction.crm_orders.count(), 0)

    def test_skips_ineligible_orders_and_transactions(self):
        kept_authorized = _at(2026, 9, 2, 12, 0, 0)
        kept_created, kept_updated = _around(kept_authorized)
        kept_website = _website(Decimal("50.00"))
        kept_order = _crm(kept_website)
        _payment(kept_website, Decimal("50.00"), kept_created, kept_updated)
        kept_tx = _online(Decimal("49.00"), kept_authorized, date(2026, 9, 3), Decimal("50.00"))

        pending_authorized = _at(2026, 9, 10, 22, 9, 36)
        pending_created, pending_updated = _around(pending_authorized)
        pending_website = _website(Decimal("65.00"))
        _crm(pending_website)
        _payment(
            pending_website,
            Decimal("65.00"),
            pending_created,
            pending_updated,
            status=LibertyPayment.STATUS_PENDING,
        )
        pending_tx = _online(Decimal("63.70"), pending_authorized, date(2026, 9, 11), Decimal("65.00"))

        test_authorized = _at(2026, 9, 11, 10, 45, 20)
        test_created, test_updated = _around(test_authorized)
        test_website = _website(Decimal("112.00"))
        _crm(test_website)
        _payment(test_website, Decimal("112.00"), test_created, test_updated, testmode=True)
        test_tx = _online(Decimal("110.10"), test_authorized, date(2026, 9, 14), Decimal("112.00"))

        cash_authorized = _at(2026, 9, 15, 14, 17, 47)
        cash_created, cash_updated = _around(cash_authorized)
        cash_website = _website(Decimal("195.00"))
        _crm(cash_website, payment_type=CrmOrder.PAYMENT_CASH)
        _payment(cash_website, Decimal("195.00"), cash_created, cash_updated)
        cash_tx = _online(Decimal("191.68"), cash_authorized, date(2026, 9, 16), Decimal("195.00"))

        unpaid_authorized = _at(2026, 9, 17, 9, 54, 37)
        unpaid_created, unpaid_updated = _around(unpaid_authorized)
        unpaid_website = _website(Decimal("60.00"))
        _crm(unpaid_website, is_paid=False)
        _payment(unpaid_website, Decimal("60.00"), unpaid_created, unpaid_updated)
        unpaid_tx = _online(Decimal("58.80"), unpaid_authorized, date(2026, 9, 18), Decimal("60.00"))

        deleted_authorized = _at(2026, 9, 19, 12, 50, 47)
        deleted_created, deleted_updated = _around(deleted_authorized)
        deleted_website = _website(Decimal("90.00"))
        _crm(deleted_website, deleted=True)
        _payment(deleted_website, Decimal("90.00"), deleted_created, deleted_updated)
        deleted_tx = _online(Decimal("88.47"), deleted_authorized, date(2026, 9, 21), Decimal("90.00"))

        linked_authorized = _at(2026, 9, 20, 16, 59, 1)
        linked_created, linked_updated = _around(linked_authorized)
        linked_website = _website(Decimal("75.00"))
        linked_order = _crm(linked_website)
        _payment(linked_website, Decimal("75.00"), linked_created, linked_updated)
        existing = FinancialTransaction.objects.create(
            account=_account(),
            date=date(2026, 9, 20),
            amount=Decimal("75.00"),
            kind=FinancialTransaction.KIND_INCOME,
            income_type=FinancialTransaction.INCOME_CASH,
        )
        existing.crm_orders.add(linked_order)
        linked_order_tx = _online(Decimal("73.50"), linked_authorized, date(2026, 9, 21), Decimal("75.00"))

        prelinked_authorized = _at(2026, 8, 28, 13, 2, 7)
        prelinked_created, prelinked_updated = _around(prelinked_authorized)
        prelinked_website = _website(Decimal("77.00"))
        prelinked_order = _crm(prelinked_website)
        _payment(prelinked_website, Decimal("77.00"), prelinked_created, prelinked_updated)
        prelinked_tx = _online(Decimal("75.69"), prelinked_authorized, date(2026, 8, 31), Decimal("77.00"))
        prelinked_tx.crm_orders.add(prelinked_order)

        broken = FinancialTransaction.objects.create(
            account=_account(),
            date=date(2026, 9, 8),
            amount=Decimal("98.00"),
            kind=FinancialTransaction.KIND_INCOME,
            income_type=FinancialTransaction.INCOME_ONLINE,
            description=f"{ONLINE_PREFIX} ORDERID 1",
        )

        sync_liberty_online_order_links()

        self.assertEqual(kept_tx.crm_orders.get().pk, kept_order.pk)
        self.assertEqual(pending_tx.crm_orders.count(), 0)
        self.assertEqual(test_tx.crm_orders.count(), 0)
        self.assertEqual(cash_tx.crm_orders.count(), 0)
        self.assertEqual(unpaid_tx.crm_orders.count(), 0)
        self.assertEqual(deleted_tx.crm_orders.count(), 0)
        self.assertEqual(linked_order_tx.crm_orders.count(), 0)
        self.assertEqual(existing.crm_orders.get().pk, linked_order.pk)
        self.assertEqual(prelinked_tx.crm_orders.get().pk, prelinked_order.pk)
        self.assertEqual(broken.crm_orders.count(), 0)

    def test_second_run_does_not_duplicate_links(self):
        authorized = _at(2026, 9, 10, 22, 9, 36)
        created, updated = _around(authorized)
        website = _website(Decimal("65.00"))
        order = _crm(website)
        _payment(website, Decimal("65.00"), created, updated)
        transaction = _online(Decimal("63.70"), authorized, date(2026, 9, 11), Decimal("65.00"))

        sync_liberty_online_order_links()
        sync_liberty_online_order_links()

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)
        self.assertEqual(FinancialTransaction.crm_orders.through.objects.count(), 1)

    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_flowwow_orders")
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_crm_order_to_telegram")
    def test_command_links_online_transaction(self, _telegram, _flowwow):
        authorized = _at(2026, 10, 7, 12, 0, 0)
        created, updated = _around(authorized)
        website = _website(Decimal("65.00"))
        order = _crm(website, date=date(2026, 10, 8))
        _payment(website, Decimal("65.00"), created, updated)
        transaction = _online(Decimal("63.70"), authorized, date(2026, 10, 8), Decimal("65.00"))

        call_command("sync_crm_orders_to_telegram")

        self.assertEqual(transaction.crm_orders.get().pk, order.pk)
