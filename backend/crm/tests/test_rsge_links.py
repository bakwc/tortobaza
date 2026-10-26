from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.test import TestCase

from crm.models import FinancialAccount, FinancialTransaction
from crm.rsge_links import sync_rsge_document_links
from rsge.models import Invoice, InvoiceLine, Waybill

_TB = ZoneInfo("Asia/Tbilisi")


def _at(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, 12, 0, tzinfo=_TB)


def _account() -> FinancialAccount:
    return FinancialAccount.objects.create(
        name="Account",
        kind=FinancialAccount.KIND_BANK,
        bank_name="Bank Of Georgia",
    )


def _expense(
    account: FinancialAccount,
    day: date,
    amount: Decimal,
    name: str,
    iban: str,
) -> FinancialTransaction:
    return FinancialTransaction.objects.create(
        account=account,
        date=day,
        amount=-amount,
        kind=FinancialTransaction.KIND_EXPENSE,
        counterparty_name=name,
        counterparty_iban=iban,
    )


def _waybill(
    rs_id: int,
    number: str,
    day: date,
    amount: Decimal,
    seller_name: str,
    seller_name_ru: str,
    seller_tin: str,
    comment: str,
    invoice_rs_id: int | None,
) -> Waybill:
    moment = _at(day)
    return Waybill.objects.create(
        rs_id=rs_id,
        waybill_number=number,
        type=1,
        status=1,
        create_date=moment,
        activate_date=moment,
        begin_date=moment,
        buyer_tin="1",
        buyer_name="Buyer",
        seller_tin=seller_tin,
        seller_name=seller_name,
        seller_name_ru=seller_name_ru,
        transport_coast=Decimal("0"),
        full_amount=amount,
        s_user_id=0,
        invoice_id=invoice_rs_id,
        is_confirmed=1,
        is_corrected=0,
        seller_st=0,
        is_med=0,
        waybill_comment=comment,
    )


def _invoice(
    rs_id: int,
    series: str,
    number: str,
    operation_day: date,
    reg_day: date,
    amount: Decimal,
    org_name: str,
    seller_tin: str,
    notes: str,
) -> Invoice:
    return Invoice.objects.create(
        rs_id=rs_id,
        seller_un_id=1,
        status=1,
        was_ref=0,
        series=series,
        number=number,
        reg_dt=_at(reg_day),
        operation_dt=_at(operation_day),
        s_user_id=0,
        b_s_user_id=0,
        seller_tin=seller_tin,
        org_name=org_name,
        amount=amount,
        vat=Decimal("0"),
        k_id=0,
        notes=notes,
    )


class SyncRsgeDocumentLinksTests(TestCase):
    def test_links_named_payments_inside_the_window(self):
        account = _account()
        cases = [
            (
                _waybill(1, "105", date(2026, 8, 15), Decimal("105.00"), "შპს ბიკო", "ООО Бико", "445568476", "", None),
                _expense(account, date(2026, 8, 16), Decimal("105.00"), "LLC  biko", "GE27BG0000000541546474GEL"),
            ),
            (
                _waybill(2, "86", date(2026, 9, 9), Decimal("86.00"), "შპს ბიკო", "ООО Бико", "445568476", "", None),
                _expense(account, date(2026, 9, 9), Decimal("86.00"), "LLC  biko", "GE27BG0000000541546474GEL"),
            ),
            (
                _waybill(3, "126", date(2026, 9, 30), Decimal("126.00"), "შპს ბიკო", "ООО Бико", "445568476", "", None),
                _expense(account, date(2026, 9, 30), Decimal("126.00"), "შპს ბიკო", "GE70TB7381436020100008"),
            ),
            (
                _waybill(4, "192", date(2026, 9, 24), Decimal("192.50"), "შპს გაგრა+", "ООО Гагра+", "250724284", "ჩარიცხულია", None),
                _expense(account, date(2026, 9, 24), Decimal("192.50"), "შპს გაგრა+", "GE54TB7850836020100009"),
            ),
            (
                _waybill(5, "222", date(2026, 9, 26), Decimal("222.17"), "შპს თურსა", "ООО Турса", "248435670", "", None),
                _expense(account, date(2026, 9, 27), Decimal("222.17"), "POS wallet - TURSA", "GE48TB0000045000000034"),
            ),
            (
                _waybill(6, "1279", date(2026, 9, 30), Decimal("1279.70"), "ია ქოქოლაძე", "Ия Коколадзе", "61006029098", "GE64BG0000000600293470GEL", None),
                _expense(account, date(2026, 10, 3), Decimal("1279.70"), "im ia kokoladze", "GE64BG0000000600293470GEL"),
            ),
            (
                _waybill(7, "277", date(2026, 9, 30), Decimal("277.00"), "შპს გ მანუფაქტურე", "ООО Г Мануфактуре", "428894342", "", None),
                _expense(account, date(2026, 9, 26), Decimal("277.00"), "G manufaqture LLC", "GE81BG0000000538282034GEL"),
            ),
            (
                _waybill(8, "649", date(2026, 10, 14), Decimal("649.60"), "შპს თურმანიძე სამი ძმა", "ООО Турманидзе", "445712532", "", None),
                _expense(account, date(2026, 10, 14), Decimal("649.60"), "market, Batumi, baTumi, kobalaZis 8a", ""),
            ),
            (
                _waybill(9, "193", date(2026, 10, 17), Decimal("193.20"), "შპს თურმანიძე სამი ძმა", "ООО Турманидзе", "445712532", "", None),
                _expense(account, date(2026, 10, 17), Decimal("193.20"), "market, Batumi, baTumi, kobalaZis 8a", ""),
            ),
            (
                _waybill(10, "182", date(2026, 10, 18), Decimal("182.30"), "შპს გორგია", "ООО Горгия", "245621288", "", None),
                _expense(account, date(2026, 10, 18), Decimal("182.30"), "GORGIA, Batumi, cjkhaidzis 1", ""),
            ),
        ]

        sync_rsge_document_links()

        for waybill, transaction in cases:
            self.assertEqual(transaction.waybills.get().pk, waybill.pk)

    def test_links_borsa_by_comment_iban(self):
        account = _account()
        waybill = _waybill(
            1,
            "256",
            date(2026, 9, 28),
            Decimal("256.00"),
            "შპს ბორსა ჯორჯია",
            "ООО Борса Джорджия",
            "445578125",
            "GE31TB7477036020100004   თიბისი ბანკი TBCBGE22",
            None,
        )
        transaction = _expense(
            account,
            date(2026, 9, 28),
            Decimal("256.00"),
            "შპს ბორსა ჯორჯია",
            "GE31TB7477036020100004",
        )

        sync_rsge_document_links()

        self.assertEqual(transaction.waybills.get().pk, waybill.pk)

    def test_biko_payment_wins_over_same_amount_cafe(self):
        account = _account()
        waybill = _waybill(
            1,
            "30",
            date(2026, 9, 10),
            Decimal("30.00"),
            "შპს ბიკო",
            "ООО Бико",
            "445568476",
            "",
            None,
        )
        biko = _expense(account, date(2026, 9, 10), Decimal("30.00"), "LLC  biko", "GE27BG0000000541546474GEL")
        aliud = _expense(account, date(2026, 9, 13), Decimal("30.00"), "POS - ALIUD UNITAS GEORGIA L", "GE48TB0000045000000034")

        sync_rsge_document_links()

        self.assertEqual(biko.waybills.get().pk, waybill.pk)
        self.assertEqual(aliud.waybills.count(), 0)

    def test_links_same_day_amounts_within_one_percent(self):
        account = _account()
        gagra = _waybill(
            1,
            "220",
            date(2026, 10, 23),
            Decimal("220.00"),
            "შპს გაგრა+",
            "ООО Гагра+",
            "250724284",
            "ტერ",
            None,
        )
        kokoladze = _waybill(
            2,
            "656",
            date(2026, 10, 23),
            Decimal("656.55"),
            "ია ქოქოლაძე",
            "Ия Коколадзе",
            "61006029098",
            "GE64BG0000000600293470GEL",
            None,
        )
        buona = _expense(account, date(2026, 10, 23), Decimal("220.00"), "BUONA SERA, Batumi", "")
        sabitumo = _expense(account, date(2026, 10, 23), Decimal("659.80"), "SABITUMO MARKETI, Batumi", "")

        sync_rsge_document_links()

        self.assertEqual(buona.waybills.get().pk, gagra.pk)
        self.assertEqual(sabitumo.waybills.get().pk, kokoladze.pk)

    def test_amount_beyond_one_percent_stays_unlinked(self):
        account = _account()
        waybill = _waybill(
            1,
            "100",
            date(2026, 10, 23),
            Decimal("100.00"),
            "შპს გაგრა+",
            "ООО Гагра+",
            "250724284",
            "",
            None,
        )
        transaction = _expense(account, date(2026, 10, 23), Decimal("102.00"), "BUONA SERA, Batumi", "")

        sync_rsge_document_links()

        self.assertEqual(transaction.waybills.count(), 0)
        self.assertEqual(waybill.financial_transactions.count(), 0)

    def test_two_waybills_within_one_percent_stay_unlinked(self):
        account = _account()
        first = _waybill(1, "100a", date(2026, 10, 23), Decimal("100.00"), "შპს გაგრა+", "ООО Гагра+", "250724284", "", None)
        second = _waybill(2, "100b", date(2026, 10, 23), Decimal("100.50"), "ია ქოქოლაძე", "Ия Коколадзе", "61006029098", "", None)
        transaction = _expense(account, date(2026, 10, 23), Decimal("100.00"), "SABITUMO MARKETI, Batumi", "")

        sync_rsge_document_links()

        self.assertEqual(transaction.waybills.count(), 0)
        self.assertEqual(first.financial_transactions.count(), 0)
        self.assertEqual(second.financial_transactions.count(), 0)

    def test_biko_card_payment_does_not_link_to_later_gagra_waybill(self):
        account = _account()
        waybill = _waybill(
            1,
            "220",
            date(2026, 10, 23),
            Decimal("220.00"),
            "შპს გაგრა+",
            "ООО Гагра+",
            "250724284",
            "ტერ",
            None,
        )
        transaction = _expense(account, date(2026, 10, 8), Decimal("220.00"), "POS wallet - Shps biko", "")

        sync_rsge_document_links()

        self.assertEqual(transaction.waybills.count(), 0)
        self.assertEqual(waybill.financial_transactions.count(), 0)

    def test_unpaid_october_documents_stay_unlinked(self):
        account = _account()
        savaneti = _waybill(1, "151", date(2026, 10, 19), Decimal("151.20"), "შპს სავანეთი 99", "ООО Саванети 99", "225372708", "", None)
        gagra = _waybill(2, "220", date(2026, 10, 23), Decimal("220.00"), "შპს გაგრა+", "ООО Гагра+", "250724284", "ტერ", None)
        kokoladze = _waybill(
            3,
            "656",
            date(2026, 10, 23),
            Decimal("656.55"),
            "ია ქოქოლაძე",
            "Ия Коколадзе",
            "61006029098",
            "GE64BG0000000600293470GEL",
            None,
        )
        _expense(account, date(2026, 10, 19), Decimal("45.05"), "loma phudi ltd, Georgia", "")

        sync_rsge_document_links()

        self.assertEqual(savaneti.financial_transactions.count(), 0)
        self.assertEqual(gagra.financial_transactions.count(), 0)
        self.assertEqual(kokoladze.financial_transactions.count(), 0)

    def test_wolt_invoice_stays_unlinked(self):
        account = _account()
        invoice = _invoice(
            1,
            "ეა-86",
            "2171335",
            date(2026, 5, 31),
            date(2026, 7, 10),
            Decimal("19.26"),
            "შპს ვოლტ ჯორჯია",
            "405260042",
            "ERP ნექსია",
        )
        transaction = _expense(account, date(2026, 7, 10), Decimal("19.26"), "POS - WOLT GEORGIA LTD", "GE48TB0000045000000034")

        sync_rsge_document_links()

        self.assertEqual(invoice.waybills.count(), 0)
        self.assertEqual(invoice.financial_transactions.count(), 0)
        self.assertEqual(transaction.invoices.count(), 0)
        self.assertEqual(transaction.waybills.count(), 0)

    def test_splits_kokoladze_payment_on_one_iban(self):
        account = _account()
        waybill = _waybill(
            1,
            "1498",
            date(2026, 7, 22),
            Decimal("1498.30"),
            "ია ქოქოლაძე",
            "Ия Коколадзе",
            "61006029098",
            "GE64BG0000000600293470GEL",
            None,
        )
        bog = _expense(account, date(2026, 7, 26), Decimal("880.00"), "IE IA KOKOLADZE", "GE64BG0000000600293470GEL")
        liberty = _expense(account, date(2026, 7, 26), Decimal("618.30"), "ია ქოქოლაძე", "GE64BG0000000600293470")

        sync_rsge_document_links()

        self.assertEqual(set(waybill.financial_transactions.values_list("pk", flat=True)), {bog.pk, liberty.pk})

    def test_links_waybill_to_invoice_by_rs_id_and_propagates_payment(self):
        account = _account()
        invoice = _invoice(
            363988109,
            "ეა-86",
            "8508123",
            date(2026, 6, 1),
            date(2026, 6, 2),
            Decimal("222.17"),
            "შპს თურსა",
            "248435670",
            "",
        )
        waybill = _waybill(
            2,
            "222",
            date(2026, 9, 26),
            Decimal("222.17"),
            "შპს თურსა",
            "ООО Турса",
            "248435670",
            "",
            363988109,
        )
        transaction = _expense(account, date(2026, 9, 27), Decimal("222.17"), "POS wallet - TURSA", "")

        sync_rsge_document_links()

        self.assertEqual(waybill.invoices.get().pk, invoice.pk)
        self.assertEqual(transaction.waybills.get().pk, waybill.pk)
        self.assertEqual(transaction.invoices.get().pk, invoice.pk)

    def test_links_waybill_to_invoice_by_line_waybill_id(self):
        invoice = _invoice(
            10,
            "ეა-86",
            "1",
            date(2026, 6, 1),
            date(2026, 6, 2),
            Decimal("159.00"),
            "შპს გორგია",
            "245621288",
            "",
        )
        waybill = _waybill(
            20,
            "159",
            date(2026, 10, 18),
            Decimal("159.00"),
            "შპს გორგია",
            "ООО Горгия",
            "245621288",
            "",
            None,
        )
        InvoiceLine.objects.create(
            invoice=invoice,
            rs_id=1,
            goods="ღუმელი",
            unit="ცალი",
            quantity=Decimal("1"),
            full_amount=Decimal("159.00"),
            vat_amount=Decimal("0"),
            excise_id=0,
            waybill_id=waybill.rs_id,
            vat_type=0,
        )

        sync_rsge_document_links()

        self.assertEqual(waybill.invoices.get().pk, invoice.pk)

    def test_links_waybill_to_invoice_by_tin_and_amount(self):
        invoice = _invoice(
            11,
            "ეა-86",
            "2",
            date(2026, 10, 16),
            date(2026, 10, 20),
            Decimal("80.00"),
            "შპს ბიკო",
            "445568476",
            "",
        )
        waybill = _waybill(
            21,
            "80",
            date(2026, 10, 18),
            Decimal("80.00"),
            "შპს ბიკო",
            "ООО Бико",
            "445568476",
            "",
            None,
        )

        sync_rsge_document_links()

        self.assertEqual(waybill.invoices.get().pk, invoice.pk)

    def test_skips_ambiguous_waybills(self):
        account = _account()
        first = _waybill(1, "40a", date(2026, 9, 1), Decimal("40.00"), "შპს ბიკო", "ООО Бико", "445568476", "", None)
        second = _waybill(2, "40b", date(2026, 9, 1), Decimal("40.00"), "შპს ბიკო", "ООО Бико", "445568476", "", None)
        transaction = _expense(account, date(2026, 9, 1), Decimal("40.00"), "LLC  biko", "")

        sync_rsge_document_links()

        self.assertEqual(transaction.waybills.count(), 0)
        self.assertEqual(first.financial_transactions.count(), 0)
        self.assertEqual(second.financial_transactions.count(), 0)

    def test_payment_five_days_away_stays_unlinked(self):
        account = _account()
        waybill = _waybill(1, "50", date(2026, 9, 1), Decimal("50.00"), "შპს ბიკო", "ООО Бико", "445568476", "", None)
        transaction = _expense(account, date(2026, 9, 6), Decimal("50.00"), "LLC  biko", "")

        sync_rsge_document_links()

        self.assertEqual(transaction.waybills.count(), 0)
        self.assertEqual(waybill.financial_transactions.count(), 0)

    def test_income_stays_unlinked(self):
        account = _account()
        waybill = _waybill(1, "86", date(2026, 9, 9), Decimal("86.00"), "შპს ბიკო", "ООО Бико", "445568476", "", None)
        transaction = FinancialTransaction.objects.create(
            account=account,
            date=date(2026, 9, 9),
            amount=Decimal("86.00"),
            kind=FinancialTransaction.KIND_INCOME,
            counterparty_name="LLC  biko",
        )

        sync_rsge_document_links()

        self.assertEqual(transaction.waybills.count(), 0)
        self.assertEqual(waybill.financial_transactions.count(), 0)

    def test_second_run_keeps_existing_link(self):
        account = _account()
        waybill = _waybill(1, "86", date(2026, 9, 9), Decimal("86.00"), "შპს ბიკო", "ООО Бико", "445568476", "", None)
        kept = _expense(account, date(2026, 9, 1), Decimal("10.00"), "someone else", "")
        pending = _expense(account, date(2026, 9, 9), Decimal("86.00"), "LLC  biko", "")
        kept.waybills.add(waybill)

        sync_rsge_document_links()
        sync_rsge_document_links()

        self.assertEqual(kept.waybills.get().pk, waybill.pk)
        self.assertEqual(pending.waybills.count(), 0)
        self.assertEqual(FinancialTransaction.waybills.through.objects.count(), 1)

    @patch("crm.management.commands.sync_crm_orders_to_telegram.translate_invoices", lambda: None)
    @patch("crm.management.commands.sync_crm_orders_to_telegram.translate_waybills", lambda: None)
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_invoices", lambda: None)
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_waybills", lambda: None)
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_flowwow_orders")
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_crm_order_to_telegram")
    def test_command_links_waybill(self, _telegram, _flowwow):
        account = _account()
        waybill = _waybill(1, "86", date(2026, 9, 9), Decimal("86.00"), "შპს ბიკო", "ООО Бико", "445568476", "", None)
        transaction = _expense(account, date(2026, 9, 9), Decimal("86.00"), "LLC  biko", "")

        call_command("sync_crm_orders_to_telegram")

        self.assertEqual(transaction.waybills.get().pk, waybill.pk)
