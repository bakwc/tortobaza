import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase

from rsge.models import Invoice, InvoiceLine, Waybill, WaybillGood
from rsge.translate import (
    TRANSLATE_MODEL,
    TRANSLATE_PROMPT,
    TranslationBatch,
    translate_invoices,
    translate_waybills,
)

TB = ZoneInfo("Asia/Tbilisi")
MOMENT = datetime(2026, 10, 14, 21, 17, 49, tzinfo=TB)


def waybill() -> Waybill:
    return Waybill.objects.create(
        rs_id=1,
        waybill_number="1014590180",
        type=3,
        status=1,
        create_date=MOMENT,
        activate_date=MOMENT,
        begin_date=MOMENT,
        buyer_tin="305523715",
        buyer_name="მყიდველი",
        buyer_name_ru="Покупатель",
        seller_tin="445712532",
        seller_name="შპს თურსა",
        transport_coast=Decimal("0"),
        full_amount=Decimal("649.6"),
        s_user_id=524645,
        is_confirmed=0,
        is_corrected=0,
        seller_st=0,
        is_med=0,
    )


def good(bill: Waybill, rs_id: int, name: str, unit_txt: str) -> WaybillGood:
    return WaybillGood.objects.create(
        waybill=bill,
        rs_id=rs_id,
        name=name,
        unit_id=2,
        unit_txt=unit_txt,
        quantity=Decimal("3"),
        price=Decimal("160"),
        amount=Decimal("480"),
        bar_code="30567",
        a_id=0,
        vat_type=0,
        status=1,
        quantity_f=Decimal("3"),
    )


def invoice() -> Invoice:
    return Invoice.objects.create(
        rs_id=364841672,
        seller_un_id=931738,
        status=1,
        was_ref=0,
        series="ეა-86",
        number="8508123",
        reg_dt=MOMENT,
        operation_dt=MOMENT,
        s_user_id=437747,
        b_s_user_id=0,
        seller_tin="248435670",
        org_name="შპს თურსა",
        notes="ERP ნექსია",
        amount=Decimal("222.17"),
        vat=Decimal("33.89"),
        k_id=-1,
    )


def line(doc: Invoice, rs_id: int, goods: str) -> InvoiceLine:
    return InvoiceLine.objects.create(
        invoice=doc,
        rs_id=rs_id,
        goods=goods,
        unit="კგ",
        quantity=Decimal("0.924"),
        full_amount=Decimal("18.48"),
        vat_amount=Decimal("2.82"),
        excise_id=0,
        vat_type=0,
    )


class WaybillTranslationTests(TestCase):
    @patch("rsge.translate.OpenAI")
    def test_translates_missing_russian_and_skips_the_next_pass(self, openai_cls):
        bill = waybill()
        cocoa = good(bill, 10, "კაკაო", "კგ")
        cocoa_again = good(bill, 11, "კაკაო", "კგ")
        tape = good(bill, 12, "ლენტი", "")
        openai_cls.return_value.responses.parse.return_value.output_parsed = TranslationBatch(
            ru=["ООО Турса", "Какао", "кг", "Лента"]
        )
        translate_waybills()
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertEqual(call["model"], TRANSLATE_MODEL)
        self.assertEqual(call["instructions"], TRANSLATE_PROMPT)
        self.assertIs(call["text_format"], TranslationBatch)
        self.assertFalse(call["store"])
        self.assertEqual(
            json.loads(call["input"]),
            ["შპს თურსა", "კაკაო", "კგ", "ლენტი"],
        )
        bill.refresh_from_db()
        cocoa.refresh_from_db()
        cocoa_again.refresh_from_db()
        tape.refresh_from_db()
        self.assertEqual(bill.seller_name_ru, "ООО Турса")
        self.assertEqual(bill.buyer_name_ru, "Покупатель")
        self.assertEqual(cocoa.name_ru, "Какао")
        self.assertEqual(cocoa.unit_txt_ru, "кг")
        self.assertEqual(cocoa_again.name_ru, "Какао")
        self.assertEqual(cocoa_again.unit_txt_ru, "кг")
        self.assertEqual(tape.name_ru, "Лента")
        self.assertEqual(tape.unit_txt_ru, "")
        openai_cls.reset_mock()
        translate_waybills()
        openai_cls.assert_not_called()

    @patch("rsge.translate.OpenAI")
    def test_empty_unit_txt_is_not_sent(self, openai_cls):
        bill = waybill()
        bill.seller_name_ru = "ООО Турса"
        bill.save(update_fields=["seller_name_ru"])
        good(bill, 10, "კაკაო", "")
        openai_cls.return_value.responses.parse.return_value.output_parsed = TranslationBatch(
            ru=["Какао"]
        )
        translate_waybills()
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertEqual(json.loads(call["input"]), ["კაკაო"])

    @patch("rsge.translate.OpenAI")
    def test_filled_waybill_is_not_selected(self, openai_cls):
        bill = waybill()
        bill.seller_name_ru = "ООО Турса"
        bill.save(update_fields=["seller_name_ru"])
        row = good(bill, 10, "კაკაო", "კგ")
        row.name_ru = "Какао"
        row.unit_txt_ru = "кг"
        row.save(update_fields=["name_ru", "unit_txt_ru"])
        translate_waybills()
        openai_cls.assert_not_called()

    @patch("rsge.translate.OpenAI")
    def test_empty_model_output_raises(self, openai_cls):
        waybill()
        openai_cls.return_value.responses.parse.return_value.output_parsed = None
        with self.assertRaises(RuntimeError):
            translate_waybills()
        self.assertEqual(Waybill.objects.get().seller_name_ru, "")

    @patch("rsge.translate.OpenAI")
    def test_length_mismatch_raises(self, openai_cls):
        bill = waybill()
        good(bill, 10, "კაკაო", "")
        openai_cls.return_value.responses.parse.return_value.output_parsed = TranslationBatch(
            ru=["ООО Турса"]
        )
        with self.assertRaises(RuntimeError):
            translate_waybills()
        self.assertEqual(Waybill.objects.get().seller_name_ru, "")


class InvoiceTranslationTests(TestCase):
    @patch("rsge.translate.OpenAI")
    def test_translates_missing_russian_and_skips_the_next_pass(self, openai_cls):
        doc = invoice()
        lime = line(doc, 20, "ლაიმი")
        lime_again = line(doc, 21, "ლაიმი")
        openai_cls.return_value.responses.parse.return_value.output_parsed = TranslationBatch(
            ru=["ООО Турса", "ERP Нексия", "Лайм", "кг"]
        )
        translate_invoices()
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertEqual(json.loads(call["input"]), ["შპს თურსა", "ERP ნექსია", "ლაიმი", "კგ"])
        doc.refresh_from_db()
        lime.refresh_from_db()
        lime_again.refresh_from_db()
        self.assertEqual(doc.org_name_ru, "ООО Турса")
        self.assertEqual(doc.notes_ru, "ERP Нексия")
        self.assertEqual(doc.note_ru, "")
        self.assertEqual(lime.goods_ru, "Лайм")
        self.assertEqual(lime.unit_ru, "кг")
        self.assertEqual(lime_again.goods_ru, "Лайм")
        self.assertEqual(lime_again.unit_ru, "кг")
        openai_cls.reset_mock()
        translate_invoices()
        openai_cls.assert_not_called()

    @patch("rsge.translate.OpenAI")
    def test_filled_invoice_is_not_selected(self, openai_cls):
        doc = invoice()
        doc.org_name_ru = "ООО Турса"
        doc.notes_ru = "ERP Нексия"
        doc.save(update_fields=["org_name_ru", "notes_ru"])
        row = line(doc, 20, "ლაიმი")
        row.goods_ru = "Лайм"
        row.unit_ru = "кг"
        row.save(update_fields=["goods_ru", "unit_ru"])
        translate_invoices()
        openai_cls.assert_not_called()
