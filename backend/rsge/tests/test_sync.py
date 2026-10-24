from datetime import date, datetime
from decimal import Decimal
from unittest.mock import call, patch
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import UserProfile
from rsge.models import Invoice, InvoiceLine, InvoiceSync, Waybill, WaybillGood, WaybillSync
from rsge.sync import sync_invoices, sync_waybills, window_start

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
        self.finance = User.objects.create_user("finance", password="x", is_staff=True)
        UserProfile.objects.create(user=self.finance, is_finance_admin=True)
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

    def test_finance_admin_lists_waybills_newest_first(self):
        self.client.force_authenticate(self.finance)
        response = self.client.get("/api/rsge/waybills/", {"month": "2026-10"})
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

    def test_other_month_is_empty(self):
        self.client.force_authenticate(self.finance)
        response = self.client.get("/api/rsge/waybills/", {"month": "2026-09"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), [])

    def test_month_is_required(self):
        self.client.force_authenticate(self.finance)
        response = self.client.get("/api/rsge/waybills/")
        self.assertEqual(response.status_code, 400)

    def test_staff_without_finance_admin_is_forbidden(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/rsge/waybills/")
        self.assertEqual(response.status_code, 403)

    @override_settings(RS_SU="su", RS_SP="sp")
    @patch("rsge.views.call_confirm_waybill")
    def test_confirm_sets_is_confirmed(self, confirm):
        self.client.force_authenticate(self.finance)
        response = self.client.post(f"/api/rsge/waybills/{self.first.pk}/confirm/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["is_confirmed"], 1)
        self.assertEqual(Waybill.objects.get(pk=self.first.pk).is_confirmed, 1)
        confirm.assert_called_once_with("su", "sp", "1")

    @override_settings(RS_SU="su", RS_SP="sp")
    @patch("rsge.views.call_reject_waybill")
    def test_reject_sets_is_confirmed(self, reject):
        self.client.force_authenticate(self.finance)
        response = self.client.post(f"/api/rsge/waybills/{self.first.pk}/reject/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["is_confirmed"], -1)
        self.assertEqual(Waybill.objects.get(pk=self.first.pk).is_confirmed, -1)
        reject.assert_called_once_with("su", "sp", "1")

    @patch("rsge.views.call_confirm_waybill")
    def test_staff_cannot_confirm(self, confirm):
        self.client.force_authenticate(self.staff)
        response = self.client.post(f"/api/rsge/waybills/{self.first.pk}/confirm/")
        self.assertEqual(response.status_code, 403)
        confirm.assert_not_called()
        self.assertEqual(Waybill.objects.get(pk=self.first.pk).is_confirmed, 0)

    @patch("rsge.views.call_reject_waybill")
    def test_staff_cannot_reject(self, reject):
        self.client.force_authenticate(self.staff)
        response = self.client.post(f"/api/rsge/waybills/{self.first.pk}/reject/")
        self.assertEqual(response.status_code, 403)
        reject.assert_not_called()
        self.assertEqual(Waybill.objects.get(pk=self.first.pk).is_confirmed, 0)

    @override_settings(RS_SU="", RS_SP="")
    @patch("rsge.views.call_confirm_waybill")
    def test_confirm_empty_credentials_raise(self, confirm):
        self.client.force_authenticate(self.finance)
        with self.assertRaises(RuntimeError):
            self.client.post(f"/api/rsge/waybills/{self.first.pk}/confirm/")
        confirm.assert_not_called()
        self.assertEqual(Waybill.objects.get(pk=self.first.pk).is_confirmed, 0)

    @override_settings(RS_SU="", RS_SP="")
    @patch("rsge.views.call_reject_waybill")
    def test_reject_empty_credentials_raise(self, reject):
        self.client.force_authenticate(self.finance)
        with self.assertRaises(RuntimeError):
            self.client.post(f"/api/rsge/waybills/{self.first.pk}/reject/")
        reject.assert_not_called()
        self.assertEqual(Waybill.objects.get(pk=self.first.pk).is_confirmed, 0)


DIFFGRAM_NS = "urn:schemas-microsoft-com:xml-diffgram-v1"


def invoice_xml(rs_id: int, status: int, reg_dt: str, agree: bool) -> str:
    agree_xml = ""
    if agree:
        agree_xml = "<AGREE_DATE>2026-10-03T10:54:15+04:00</AGREE_DATE><AGREE_S_USER_ID>437747</AGREE_S_USER_ID>"
    return f"""
    <invoices>
      <ID>{rs_id}</ID>
      <SELLER_UN_ID>931738</SELLER_UN_ID>
      <STATUS>{status}</STATUS>
      <WAS_REF>0</WAS_REF>
      <F_SERIES>ეა-86</F_SERIES>
      <F_NUMBER>8508123</F_NUMBER>
      <REG_DT>{reg_dt}</REG_DT>
      <OPERATION_DT>2026-09-26T18:18:46+04:00</OPERATION_DT>
      <S_USER_ID>437747</S_USER_ID>
      <B_S_USER_ID>0</B_S_USER_ID>
      <SA_IDENT_NO>248435670</SA_IDENT_NO>
      <ORG_NAME>შპს თურსა</ORG_NAME>
      <NOTES>apex</NOTES>
      <TANXA>222.17</TANXA>
      <VAT>33.89</VAT>
      <K_ID>-1</K_ID>
      {agree_xml}
    </invoices>
    """


def line_xml(rs_id: int, inv_id: int, goods: str, quantity: str) -> str:
    return f"""
    <invoices_descs>
      <ID>{rs_id}</ID>
      <INV_ID>{inv_id}</INV_ID>
      <GOODS>{goods}</GOODS>
      <G_UNIT>კგ</G_UNIT>
      <G_NUMBER>{quantity}</G_NUMBER>
      <FULL_AMOUNT>18.48</FULL_AMOUNT>
      <DRG_AMOUNT>2.82</DRG_AMOUNT>
      <AKCIS_ID>0</AKCIS_ID>
      <VAT_TYPE>0</VAT_TYPE>
    </invoices_descs>
    """


def diffgram_result(*rows: str) -> ET.Element:
    body = "".join(rows)
    return ET.fromstring(
        f"""<Result>
          <diffgram xmlns="{DIFFGRAM_NS}">
            <DocumentElement xmlns="">{body}</DocumentElement>
          </diffgram>
        </Result>"""
    )


def empty_invoices() -> ET.Element:
    return ET.fromstring(f'<Result><diffgram xmlns="{DIFFGRAM_NS}" /></Result>')


def stored_invoice(rs_id: int) -> Invoice:
    moment = datetime(2026, 10, 1, 12, 0, tzinfo=TB)
    return Invoice.objects.create(
        rs_id=rs_id,
        seller_un_id=1,
        status=1,
        was_ref=0,
        series="old",
        number=str(rs_id),
        reg_dt=moment,
        operation_dt=moment,
        s_user_id=0,
        b_s_user_id=0,
        seller_tin="1",
        org_name="Old org",
        amount=Decimal("1"),
        vat=Decimal("0"),
        k_id=-1,
    )


@override_settings(RS_SU="su", RS_SP="sp")
class InvoiceSyncTests(TestCase):
    @patch("rsge.sync.timezone.now", return_value=NOW)
    @patch("rsge.client.call_get_invoice_desc")
    @patch("rsge.client.call_get_buyer_invoices")
    @patch("rsge.sync.call_get_un_id", return_value="931738")
    @patch("rsge.sync.call_chek", return_value="437747")
    def test_recent_sync_requests_the_last_three_days(self, chek, un_id, buyer, detail, _now):
        InvoiceSync.objects.create(synced_at=datetime(2026, 10, 23, 15, 0, tzinfo=TB))
        buyer.return_value = empty_invoices()
        sync_invoices()
        self.assertEqual(chek.call_args_list, [call("su", "sp")])
        self.assertEqual(un_id.call_args_list, [call("su", "sp", "437747")])
        self.assertEqual(
            [item.args[4:] for item in buyer.call_args_list],
            [
                ("2026-10-21T00:00:00", "2026-10-24T00:00:00"),
                ("2026-10-24T00:00:00", "2026-10-25T00:00:00"),
            ],
        )
        self.assertEqual(buyer.call_args_list[0].args[:4], ("su", "sp", "437747", "931738"))
        detail.assert_not_called()
        self.assertEqual(InvoiceSync.objects.get().synced_at, NOW)

    @patch("rsge.sync.timezone.now", return_value=NOW)
    @patch("rsge.client.call_get_invoice_desc")
    @patch("rsge.client.call_get_buyer_invoices")
    @patch("rsge.sync.call_get_un_id", return_value="931738")
    @patch("rsge.sync.call_chek", return_value="437747")
    def test_existing_invoice_is_not_fetched_again(self, chek, un_id, buyer, detail, _now):
        existing = stored_invoice(363988109)
        InvoiceSync.objects.create(synced_at=datetime(2026, 10, 23, 8, 0, tzinfo=TB))
        buyer.return_value = diffgram_result(
            invoice_xml(363988109, 9, "2026-10-02T18:29:21+04:00", True),
            invoice_xml(364841672, 1, "2026-10-11T21:51:47+04:00", False),
        )
        detail.return_value = diffgram_result(
            line_xml(4670731325, 364841672, "ლაიმი", "0.924"),
            line_xml(4670731326, 364841672, "ბანანი", "2.016"),
        )
        sync_invoices()
        self.assertEqual(detail.call_args_list, [call("su", "sp", "437747", "364841672")])
        existing.refresh_from_db()
        self.assertEqual(existing.status, 1)
        self.assertEqual(existing.org_name, "Old org")
        self.assertEqual(existing.lines.count(), 0)
        created = Invoice.objects.get(rs_id=364841672)
        self.assertEqual(created.series, "ეა-86")
        self.assertEqual(created.number, "8508123")
        self.assertEqual(created.org_name, "შპს თურსა")
        self.assertEqual(created.notes, "apex")
        self.assertEqual(created.seller_tin, "248435670")
        self.assertEqual(created.amount, Decimal("222.17"))
        self.assertEqual(created.vat, Decimal("33.89"))
        self.assertEqual(created.status, 1)
        self.assertIsNone(created.agree_date)
        self.assertIsNone(created.seq_num_b)
        self.assertEqual(created.doc_mos_nom, "")
        self.assertEqual(created.note, "")
        self.assertEqual(created.reg_dt, datetime.fromisoformat("2026-10-11T21:51:47+04:00"))
        self.assertEqual(created.operation_dt, datetime.fromisoformat("2026-09-26T18:18:46+04:00"))
        lime = created.lines.get(rs_id=4670731325)
        banana = created.lines.get(rs_id=4670731326)
        self.assertEqual(lime.goods, "ლაიმი")
        self.assertEqual(lime.unit, "კგ")
        self.assertEqual(lime.quantity, Decimal("0.924"))
        self.assertEqual(lime.full_amount, Decimal("18.48"))
        self.assertEqual(lime.vat_amount, Decimal("2.82"))
        self.assertIsNone(lime.excise_amount)
        self.assertIsNone(lime.waybill_id)
        self.assertEqual(lime.excise_id, 0)
        self.assertEqual(banana.quantity, Decimal("2.016"))
        self.assertEqual(InvoiceSync.objects.get().synced_at, NOW)
        chek.assert_called_once_with("su", "sp")
        un_id.assert_called_once_with("su", "sp", "437747")

    @patch("rsge.sync.timezone.now", return_value=NOW)
    @patch("rsge.client.call_get_invoice_desc")
    @patch("rsge.client.call_get_buyer_invoices")
    @patch("rsge.sync.call_get_un_id", return_value="931738")
    @patch("rsge.sync.call_chek", return_value="437747")
    def test_agreed_invoice_keeps_offset_and_lines(self, _chek, _un_id, buyer, detail, _now):
        InvoiceSync.objects.create(synced_at=datetime(2026, 10, 23, 8, 0, tzinfo=TB))
        buyer.return_value = diffgram_result(
            invoice_xml(363988109, 2, "2026-10-02T18:29:21+04:00", True),
        )
        detail.return_value = diffgram_result(line_xml(4670731325, 363988109, "ლაიმი", "0.924"))
        sync_invoices()
        created = Invoice.objects.get(rs_id=363988109)
        self.assertEqual(created.status, 2)
        self.assertEqual(created.agree_date, datetime.fromisoformat("2026-10-03T10:54:15+04:00"))
        self.assertEqual(created.agree_s_user_id, 437747)
        self.assertEqual(created.reg_dt, datetime.fromisoformat("2026-10-02T18:29:21+04:00"))
        self.assertEqual(created.lines.count(), 1)

    @patch("rsge.sync.timezone.now", return_value=NOW)
    @patch("rsge.client.call_get_invoice_desc")
    @patch("rsge.client.call_get_buyer_invoices")
    @patch("rsge.sync.call_get_un_id", return_value="931738")
    @patch("rsge.sync.call_chek", return_value="437747")
    def test_failed_chunk_keeps_saved_invoices_and_synced_at(self, _chek, _un_id, buyer, detail, _now):
        old = datetime(2026, 10, 10, 8, 0, tzinfo=TB)
        InvoiceSync.objects.create(synced_at=old)

        def lists(su, sp, user_id, un_id, start, end):
            if start == "2026-10-10T00:00:00":
                return diffgram_result(invoice_xml(5, 2, "2026-10-02T18:29:21+04:00", True))
            if start == "2026-10-13T00:00:00":
                return ET.fromstring("<Result><STATUS>-1</STATUS></Result>")
            return empty_invoices()

        buyer.side_effect = lists
        detail.return_value = diffgram_result(line_xml(10, 5, "ლაიმი", "1"))
        with self.assertRaises(RuntimeError):
            sync_invoices()
        self.assertEqual(Invoice.objects.get(rs_id=5).lines.count(), 1)
        self.assertEqual(InvoiceSync.objects.get().synced_at, old)
        self.assertEqual(detail.call_args_list, [call("su", "sp", "437747", "5")])

    @override_settings(RS_SU="", RS_SP="")
    @patch("rsge.sync.call_chek")
    def test_empty_credentials_raise(self, chek):
        with self.assertRaises(RuntimeError):
            sync_invoices()
        chek.assert_not_called()
        self.assertEqual(InvoiceSync.objects.count(), 0)


class InvoiceApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user("boss", password="x", is_staff=True)
        self.finance = User.objects.create_user("finance", password="x", is_staff=True)
        UserProfile.objects.create(user=self.finance, is_finance_admin=True)
        older = datetime(2026, 10, 2, 18, 29, 21, tzinfo=TB)
        newer = datetime(2026, 10, 11, 21, 51, 47, tzinfo=TB)
        first = Invoice.objects.create(
            rs_id=363988109,
            seller_un_id=931738,
            status=2,
            was_ref=0,
            series="ეა-86",
            number="8508123",
            reg_dt=older,
            operation_dt=older,
            s_user_id=437747,
            b_s_user_id=0,
            seller_tin="248435670",
            org_name="შპს თურსა",
            notes="apex",
            amount=Decimal("222.17"),
            vat=Decimal("33.89"),
            k_id=-1,
            agree_date=datetime(2026, 10, 3, 10, 54, 15, tzinfo=TB),
        )
        second = Invoice.objects.create(
            rs_id=364841672,
            seller_un_id=2719091,
            status=1,
            was_ref=0,
            series="ეა-86",
            number="9392733",
            reg_dt=newer,
            operation_dt=newer,
            s_user_id=507792,
            b_s_user_id=0,
            seller_tin="405260042",
            org_name="შპს ვოლტ ჯორჯია",
            notes="ERP ნექსია",
            amount=Decimal("21.24"),
            vat=Decimal("3.24"),
            k_id=-1,
        )
        InvoiceLine.objects.create(
            invoice=second,
            rs_id=4686329596,
            goods="Wolt service",
            unit="მომსახურება",
            quantity=Decimal("0"),
            full_amount=Decimal("21.24"),
            vat_amount=Decimal("3.24"),
            excise_id=0,
            vat_type=0,
        )
        self.first = first

    def test_finance_admin_lists_invoices_newest_first(self):
        self.client.force_authenticate(self.finance)
        response = self.client.get("/api/rsge/invoices/", {"month": "2026-10"})
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual([row["rs_id"] for row in payload], [364841672, 363988109])
        self.assertEqual(payload[0]["number"], "9392733")
        self.assertEqual(payload[0]["org_name"], "შპს ვოლტ ჯორჯია")
        self.assertEqual(payload[0]["notes"], "ERP ნექსია")
        self.assertEqual(payload[0]["lines"][0]["goods"], "Wolt service")
        self.assertEqual(payload[0]["lines"][0]["unit"], "მომსახურება")
        self.assertIsNone(payload[0]["lines"][0]["excise_amount"])
        self.assertIsNone(payload[0]["agree_date"])
        self.assertEqual(payload[1]["lines"], [])
        self.assertEqual(payload[1]["notes"], "apex")
        self.assertIsNotNone(payload[1]["agree_date"])
        self.assertEqual(payload[1]["id"], self.first.pk)

    def test_other_month_is_empty(self):
        self.client.force_authenticate(self.finance)
        response = self.client.get("/api/rsge/invoices/", {"month": "2026-09"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), [])

    def test_month_is_required(self):
        self.client.force_authenticate(self.finance)
        response = self.client.get("/api/rsge/invoices/")
        self.assertEqual(response.status_code, 400)

    def test_staff_without_finance_admin_is_forbidden(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/rsge/invoices/")
        self.assertEqual(response.status_code, 403)
