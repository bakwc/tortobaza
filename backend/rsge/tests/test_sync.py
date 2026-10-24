from datetime import date, datetime
from decimal import Decimal
from unittest.mock import call, patch
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from rsge.models import Waybill, WaybillGood, WaybillSync
from rsge.sync import sync_waybills, window_start

TB = ZoneInfo("Asia/Tbilisi")
NOW = datetime(2026, 10, 24, 12, 0, tzinfo=TB)


def waybill_xml(rs_id: int, status: int) -> str:
    return f"""
    <WAYBILL>
      <ID>{rs_id}</ID>
      <TYPE>3</TYPE>
      <CREATE_DATE>2026-10-14T21:17:49</CREATE_DATE>
      <BUYER_TIN>305523715</BUYER_TIN>
      <BUYER_NAME>Buyer</BUYER_NAME>
      <SELLER_NAME>Seller</SELLER_NAME>
      <SELLER_TIN>445712532</SELLER_TIN>
      <START_ADDRESS>Start</START_ADDRESS>
      <TRANSPORT_COAST>0</TRANSPORT_COAST>
      <STATUS>{status}</STATUS>
      <ACTIVATE_DATE>2026-10-14T21:17:49</ACTIVATE_DATE>
      <FULL_AMOUNT>649.6</FULL_AMOUNT>
      <WAYBILL_NUMBER>1014590180</WAYBILL_NUMBER>
      <S_USER_ID>524645</S_USER_ID>
      <BEGIN_DATE>2026-10-14T21:17:51</BEGIN_DATE>
      <IS_CONFIRMED>0</IS_CONFIRMED>
      <IS_CORRECTED>0</IS_CORRECTED>
      <SELLER_ST>0</SELLER_ST>
      <IS_MED>0</IS_MED>
    </WAYBILL>
    """


def list_result(*bodies: str) -> ET.Element:
    inner = "".join(f"<WAYBILL_LIST>{body}</WAYBILL_LIST>" for body in bodies)
    return ET.fromstring(f"<Result>{inner}</Result>")


def empty_list() -> ET.Element:
    return ET.fromstring("<Result><WAYBILL_LIST /></Result>")


def goods_xml() -> ET.Element:
    return ET.fromstring(
        """
        <Result>
          <GOODS>
            <ID>6260693589</ID>
            <W_NAME>Cocoa</W_NAME>
            <UNIT_ID>2</UNIT_ID>
            <QUANTITY>3</QUANTITY>
            <PRICE>160</PRICE>
            <AMOUNT>480</AMOUNT>
            <BAR_CODE>30567</BAR_CODE>
            <A_ID>0</A_ID>
            <VAT_TYPE>0</VAT_TYPE>
            <STATUS>1</STATUS>
            <QUANTITY_F>3</QUANTITY_F>
          </GOODS>
          <GOODS>
            <ID>6260693590</ID>
            <W_NAME>Tape</W_NAME>
            <UNIT_ID>99</UNIT_ID>
            <UNIT_TXT>pack</UNIT_TXT>
            <QUANTITY>8</QUANTITY>
            <PRICE>.4</PRICE>
            <AMOUNT>3.2</AMOUNT>
            <BAR_CODE>6946</BAR_CODE>
            <A_ID>0</A_ID>
            <VAT_TYPE>0</VAT_TYPE>
            <QUANTITY_EXT>0</QUANTITY_EXT>
            <STATUS>1</STATUS>
            <QUANTITY_F>8</QUANTITY_F>
          </GOODS>
        </Result>
        """
    )


def stored_waybill(rs_id: int) -> Waybill:
    moment = datetime(2026, 10, 1, 12, 0, tzinfo=TB)
    return Waybill.objects.create(
        rs_id=rs_id,
        waybill_number=f"old-{rs_id}",
        type=2,
        status=1,
        create_date=moment,
        activate_date=moment,
        begin_date=moment,
        buyer_tin="1",
        buyer_name="Old buyer",
        seller_tin="2",
        seller_name="Old seller",
        transport_coast=Decimal("0"),
        full_amount=Decimal("1"),
        s_user_id=0,
        is_confirmed=0,
        is_corrected=0,
        seller_st=0,
        is_med=0,
    )


class WindowStartTests(TestCase):
    def test_no_sync_starts_thirty_days_back(self):
        self.assertEqual(window_start(NOW, None), date(2026, 9, 24))

    def test_recent_sync_looks_back_three_days(self):
        last = datetime(2026, 10, 23, 12, 0, tzinfo=TB)
        self.assertEqual(window_start(NOW, last), date(2026, 10, 21))

    def test_older_sync_starts_on_its_date(self):
        last = datetime(2026, 10, 10, 8, 0, tzinfo=TB)
        self.assertEqual(window_start(NOW, last), date(2026, 10, 10))

    def test_sync_older_than_a_month_is_clamped(self):
        last = datetime(2026, 8, 1, 8, 0, tzinfo=TB)
        self.assertEqual(window_start(NOW, last), date(2026, 9, 24))

    def test_sync_at_least_three_days_ago_uses_its_date(self):
        last = datetime(2026, 10, 20, 18, 0, tzinfo=TB)
        self.assertEqual(window_start(NOW, last), date(2026, 10, 20))


@override_settings(RS_SU="su", RS_SP="sp")
class WaybillSyncTests(TestCase):
    @patch("rsge.sync.timezone.now", return_value=NOW)
    @patch("rsge.client.call_get_waybill")
    @patch("rsge.client.call_get_buyer_waybills")
    def test_older_sync_requests_three_day_chunks(self, buyer, detail, _now):
        WaybillSync.objects.create(synced_at=datetime(2026, 10, 10, 8, 0, tzinfo=TB))
        buyer.return_value = empty_list()
        sync_waybills()
        self.assertEqual(
            [item.args[2:] for item in buyer.call_args_list],
            [
                ("2026-10-10T00:00:00", "2026-10-13T00:00:00"),
                ("2026-10-13T00:00:00", "2026-10-16T00:00:00"),
                ("2026-10-16T00:00:00", "2026-10-19T00:00:00"),
                ("2026-10-19T00:00:00", "2026-10-22T00:00:00"),
                ("2026-10-22T00:00:00", "2026-10-25T00:00:00"),
            ],
        )
        detail.assert_not_called()
        self.assertEqual(WaybillSync.objects.get().synced_at, NOW)

    @patch("rsge.sync.timezone.now", return_value=NOW)
    @patch("rsge.client.call_get_waybill")
    @patch("rsge.client.call_get_buyer_waybills")
    def test_recent_sync_requests_the_last_three_days(self, buyer, detail, _now):
        WaybillSync.objects.create(synced_at=datetime(2026, 10, 23, 15, 0, tzinfo=TB))
        buyer.return_value = empty_list()
        sync_waybills()
        self.assertEqual(
            [item.args[2:] for item in buyer.call_args_list],
            [
                ("2026-10-21T00:00:00", "2026-10-24T00:00:00"),
                ("2026-10-24T00:00:00", "2026-10-25T00:00:00"),
            ],
        )
        detail.assert_not_called()

    @patch("rsge.sync.timezone.now", return_value=NOW)
    @patch("rsge.client.call_get_buyer_waybills")
    def test_first_sync_starts_a_month_ago(self, buyer, _now):
        buyer.return_value = empty_list()
        sync_waybills()
        ranges = [item.args[2:] for item in buyer.call_args_list]
        self.assertEqual(ranges[0], ("2026-09-24T00:00:00", "2026-09-27T00:00:00"))
        self.assertEqual(ranges[-1], ("2026-10-24T00:00:00", "2026-10-25T00:00:00"))
        self.assertEqual(len(ranges), 11)

    @patch("rsge.sync.timezone.now", return_value=NOW)
    @patch("rsge.client.call_get_buyer_waybills")
    def test_sync_older_than_a_month_starts_a_month_ago(self, buyer, _now):
        WaybillSync.objects.create(synced_at=datetime(2026, 8, 1, 8, 0, tzinfo=TB))
        buyer.return_value = empty_list()
        sync_waybills()
        self.assertEqual(buyer.call_args_list[0].args[2:], ("2026-09-24T00:00:00", "2026-09-27T00:00:00"))

    @patch("rsge.sync.timezone.now", return_value=NOW)
    @patch("rsge.client.call_get_waybill")
    @patch("rsge.client.call_get_buyer_waybills")
    def test_existing_waybill_is_not_fetched_again(self, buyer, detail, _now):
        existing = stored_waybill(1)
        WaybillSync.objects.create(synced_at=datetime(2026, 10, 23, 8, 0, tzinfo=TB))
        buyer.return_value = list_result(waybill_xml(1, 9), waybill_xml(2, 1))
        detail.return_value = goods_xml()
        sync_waybills()
        self.assertEqual(detail.call_args_list, [call("su", "sp", "2")])
        existing.refresh_from_db()
        self.assertEqual(existing.status, 1)
        self.assertEqual(existing.seller_name, "Old seller")
        self.assertEqual(existing.goods.count(), 0)
        created = Waybill.objects.get(rs_id=2)
        self.assertEqual(created.seller_name, "Seller")
        self.assertEqual(created.start_address, "Start")
        self.assertEqual(created.end_address, "")
        self.assertEqual(created.full_amount, Decimal("649.6"))
        self.assertEqual(created.create_date, datetime(2026, 10, 14, 21, 17, 49, tzinfo=TB))
        self.assertEqual(created.status, 1)
        cocoa = created.goods.get(rs_id=6260693589)
        tape = created.goods.get(rs_id=6260693590)
        self.assertEqual(cocoa.bar_code, "30567")
        self.assertIsNone(cocoa.quantity_ext)
        self.assertEqual(tape.unit_txt, "pack")
        self.assertEqual(tape.price, Decimal("0.4"))
        self.assertEqual(tape.quantity_ext, Decimal("0"))
        self.assertEqual(WaybillSync.objects.get().synced_at, NOW)

    @patch("rsge.sync.timezone.now", return_value=NOW)
    @patch("rsge.client.call_get_waybill")
    @patch("rsge.client.call_get_buyer_waybills")
    def test_failed_chunk_keeps_saved_waybills_and_synced_at(self, buyer, detail, _now):
        old = datetime(2026, 10, 10, 8, 0, tzinfo=TB)
        WaybillSync.objects.create(synced_at=old)

        def lists(su, sp, start, end):
            if start == "2026-10-10T00:00:00":
                return list_result(waybill_xml(5, 1))
            if start == "2026-10-13T00:00:00":
                return ET.fromstring("<Result><STATUS>-1</STATUS></Result>")
            return empty_list()

        buyer.side_effect = lists
        detail.return_value = goods_xml()
        with self.assertRaises(RuntimeError):
            sync_waybills()
        self.assertEqual(Waybill.objects.get(rs_id=5).goods.count(), 2)
        self.assertEqual(WaybillSync.objects.get().synced_at, old)
        self.assertEqual(detail.call_args_list, [call("su", "sp", "5")])

    @override_settings(RS_SU="", RS_SP="")
    @patch("rsge.client.call_get_buyer_waybills")
    def test_empty_credentials_raise(self, buyer):
        with self.assertRaises(RuntimeError):
            sync_waybills()
        buyer.assert_not_called()
        self.assertEqual(WaybillSync.objects.count(), 0)


class WaybillApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user("boss", password="x", is_staff=True)
        self.worker = User.objects.create_user("worker", password="x")
        older = datetime(2026, 10, 1, 12, 0, tzinfo=TB)
        newer = datetime(2026, 10, 14, 21, 17, 49, tzinfo=TB)
        first = Waybill.objects.create(
            rs_id=1,
            waybill_number="old",
            type=2,
            status=2,
            create_date=older,
            activate_date=older,
            begin_date=older,
            buyer_tin="1",
            buyer_name="Buyer",
            seller_tin="2",
            seller_name="Old seller",
            transport_coast=Decimal("0"),
            full_amount=Decimal("10"),
            s_user_id=1,
            is_confirmed=0,
            is_corrected=0,
            seller_st=0,
            is_med=0,
        )
        second = Waybill.objects.create(
            rs_id=2,
            waybill_number="1014590180",
            type=3,
            status=1,
            create_date=newer,
            activate_date=newer,
            begin_date=newer,
            buyer_tin="305523715",
            buyer_name="Buyer",
            seller_tin="445712532",
            seller_name="Seller",
            transport_coast=Decimal("0"),
            full_amount=Decimal("649.6"),
            s_user_id=524645,
            is_confirmed=0,
            is_corrected=0,
            seller_st=0,
            is_med=0,
        )
        WaybillGood.objects.create(
            waybill=second,
            rs_id=10,
            name="Cocoa",
            unit_id=2,
            quantity=Decimal("3"),
            price=Decimal("160"),
            amount=Decimal("480"),
            bar_code="30567",
            a_id=0,
            vat_type=0,
            status=1,
            quantity_f=Decimal("3"),
        )
        self.first = first

    def test_staff_lists_waybills_newest_first(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/rsge/waybills/")
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual([row["rs_id"] for row in payload], [2, 1])
        self.assertEqual(payload[0]["waybill_number"], "1014590180")
        self.assertEqual(payload[0]["seller_name"], "Seller")
        self.assertEqual(payload[0]["goods"][0]["name"], "Cocoa")
        self.assertEqual(payload[0]["goods"][0]["bar_code"], "30567")
        self.assertIsNone(payload[0]["goods"][0]["quantity_ext"])
        self.assertEqual(payload[1]["goods"], [])
        self.assertEqual(payload[1]["id"], self.first.pk)

    def test_non_staff_is_forbidden(self):
        self.client.force_authenticate(self.worker)
        response = self.client.get("/api/rsge/waybills/")
        self.assertEqual(response.status_code, 403)
