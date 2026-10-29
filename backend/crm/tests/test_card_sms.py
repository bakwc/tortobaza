from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from crm.card_sms import (
    InboxMessage,
    fetch_recent_test_messages,
    html_to_text,
    import_card_sms,
    parse_card_sms,
)
from crm.models import CardSmsMessage, FinancialAccount, FinancialTransaction
from tortobaza.finance_db import use_finance_db

_TB = ZoneInfo("Asia/Tbilisi")
GEL_HTML = (
    "Purchase: GEL66.56<br/>Card:***3319<br/>Wolt<br/>"
    "you received: 149.76 PLUS<br/>Total: 432,690.94 PLUS<br/>26.10.2026"
)
USD_HTML = (
    "Purchase: USD50.00<br/>Card:***1996<br/>"
    "FACEBK* D4D8PDAQM4&gt;+35315530550 IE<br/>27.10.2026"
)
GASAVLI_HTML = (
    "gasavali<br/>individualuri mecarme pilipp bakanov<br/>GEL151.20<br/>"
    "SWEET CHILL<br/>nashti: GEL1,629.34<br/>24/10/2026"
)
CHARICXVA_HTML = (
    "charicxva<br/>individualuri mecarme pilipp bakanov<br/>GEL325.84<br/>"
    "SWEET CHILL<br/>visgan: LTD WISE PAYMENTS<br/>nashti: GEL1,780.54<br/>23/10/2026"
)
PAYMENT_HTML = (
    "Payment: GEL50.00<br/>GE30***1239GEL<br/>Magti Internet Services<br/>"
    "You received: 112.50 PLUS<br/>Total: 433,767.95 PLUS<br/>29.10.2026"
)
PAYMENT_IBAN = "GE30BG0000000000001239GEL"


class FakeIMAP:
    def __init__(self, messages: dict[bytes, bytes]):
        self.messages = messages
        self.criteria = ()

    def login(self, user: str, password: str):
        return "OK", []

    def select(self, mailbox: str):
        return "OK", [b"1"]

    def search(self, charset, *criteria):
        self.criteria = criteria
        return "OK", [b" ".join(self.messages)]

    def fetch(self, number: bytes, query: str):
        raw = self.messages[number]
        meta = b'1 (INTERNALDATE "26-Oct-2026 03:00:00 +0400" BODY[] {1}'
        return "OK", [(meta, raw)]

    def logout(self):
        return "OK", [b"BYE"]


def _raw(message_id: str, date_header: str, subject: str, html: str) -> bytes:
    headers = [
        f"Date: {date_header}",
        f"Subject: {subject}",
        "MIME-Version: 1.0",
        "Content-Type: text/html; charset=utf-8",
    ]
    if message_id != "":
        headers.insert(0, f"Message-ID: {message_id}")
    return ("\r\n".join(headers) + "\r\n\r\n" + html).encode()


def _message(message_id: str, html: str) -> InboxMessage:
    return InboxMessage(
        message_id=message_id,
        received_at=datetime(2026, 10, 27, 12, 0, tzinfo=_TB),
        body=html_to_text(html),
    )


def _import(messages: list[InboxMessage]) -> None:
    with patch("crm.card_sms.fetch_recent_test_messages", return_value=messages):
        import_card_sms()


def _account(name: str, currency: str, cards: str, alias: str) -> FinancialAccount:
    with use_finance_db(alias):
        return FinancialAccount.objects.create(
            name=name,
            kind=FinancialAccount.KIND_BANK,
            currency=currency,
            cards=cards,
        )


def _transactions(alias: str) -> list[FinancialTransaction]:
    with use_finance_db(alias):
        return list(FinancialTransaction.objects.order_by("id"))


class CardSmsTests(TestCase):
    databases = {"default", "personal"}

    def test_parse_purchase_examples(self):
        gel = parse_card_sms(html_to_text(GEL_HTML))
        self.assertIsNotNone(gel)
        self.assertEqual(gel.currency, "GEL")
        self.assertEqual(gel.amount, Decimal("66.56"))
        self.assertEqual(gel.card_last4, "3319")
        self.assertEqual(gel.merchant, "Wolt")
        self.assertEqual(gel.sms_date, date(2026, 10, 26))
        usd = parse_card_sms(html_to_text(USD_HTML))
        self.assertIsNotNone(usd)
        self.assertEqual(usd.currency, "USD")
        self.assertEqual(usd.amount, Decimal("50.00"))
        self.assertEqual(usd.card_last4, "1996")
        self.assertEqual(usd.merchant, "FACEBK* D4D8PDAQM4>+35315530550 IE")
        self.assertEqual(usd.sms_date, date(2026, 10, 27))
        self.assertEqual(gel.kind, CardSmsMessage.KIND_EXPENSE)

    def test_parse_account_operations(self):
        expense = parse_card_sms(html_to_text(GASAVLI_HTML))
        self.assertIsNotNone(expense)
        self.assertEqual(expense.card_last4, "")
        self.assertEqual(expense.currency, "GEL")
        self.assertEqual(expense.amount, Decimal("151.20"))
        self.assertEqual(expense.merchant, "SWEET CHILL")
        self.assertEqual(expense.sms_date, date(2026, 10, 24))
        self.assertEqual(expense.kind, CardSmsMessage.KIND_EXPENSE)
        income = parse_card_sms(html_to_text(CHARICXVA_HTML))
        self.assertIsNotNone(income)
        self.assertEqual(income.card_last4, "")
        self.assertEqual(income.currency, "GEL")
        self.assertEqual(income.amount, Decimal("325.84"))
        self.assertEqual(income.merchant, "LTD WISE PAYMENTS")
        self.assertEqual(income.sms_date, date(2026, 10, 23))
        self.assertEqual(income.kind, CardSmsMessage.KIND_INCOME)
        dotted = parse_card_sms(html_to_text(GASAVLI_HTML.replace("24/10/2026", "24.10.2026")))
        self.assertIsNotNone(dotted)
        self.assertEqual(dotted.sms_date, date(2026, 10, 24))
        self.assertEqual(dotted.amount, Decimal("151.20"))

    def test_parse_payment(self):
        parsed = parse_card_sms(html_to_text(PAYMENT_HTML))
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.card_last4, "")
        self.assertEqual(parsed.currency, "GEL")
        self.assertEqual(parsed.amount, Decimal("50.00"))
        self.assertEqual(parsed.merchant, "Magti Internet Services")
        self.assertEqual(parsed.sms_date, date(2026, 10, 29))
        self.assertEqual(parsed.kind, CardSmsMessage.KIND_EXPENSE)
        self.assertEqual(parsed.account_prefix, "GE30")
        self.assertEqual(parsed.account_suffix, "1239")

    def test_payment_sms_matches_iban_mask(self):
        account = _account("Masked GEL", "GEL", "", "default")
        account.iban = PAYMENT_IBAN
        account.save(update_fields=["iban"])
        card_only = _account("Card only", "GEL", "1239", "default")
        _account("BOG business GEL", "GEL", "", "personal")
        _import([_message("<pay@gmail.com>", PAYMENT_HTML)])
        rows = _transactions("default")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].account_id, account.pk)
        self.assertNotEqual(rows[0].account_id, card_only.pk)
        self.assertEqual(rows[0].amount, Decimal("-50.00"))
        self.assertEqual(rows[0].kind, FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(rows[0].counterparty_name, "Magti Internet Services")
        self.assertEqual(rows[0].description, "Magti Internet Services")
        self.assertEqual(rows[0].date, date(2026, 10, 29))
        self.assertEqual(rows[0].external_id, "<pay@gmail.com>")
        self.assertEqual(_transactions("personal"), [])
        stored = CardSmsMessage.objects.get(message_id="<pay@gmail.com>")
        self.assertEqual(stored.card_last4, "")
        self.assertEqual(stored.status, CardSmsMessage.STATUS_INSERTED)
        self.assertEqual(stored.finance_db, "default")
        self.assertEqual(stored.transaction_id, rows[0].pk)

    def test_payment_sms_ignores_card_and_named_account(self):
        _account("Card only", "GEL", "1239", "default")
        _account("BOG business GEL", "GEL", "", "default")
        _import([_message("<pay@gmail.com>", PAYMENT_HTML)])
        self.assertEqual(_transactions("default"), [])
        self.assertEqual(_transactions("personal"), [])
        row = CardSmsMessage.objects.get()
        self.assertEqual(row.status, CardSmsMessage.STATUS_UNMATCHED)
        self.assertEqual(row.card_last4, "")
        self.assertEqual(row.amount, Decimal("50.00"))
        self.assertEqual(row.merchant, "Magti Internet Services")

    def test_payment_sms_ambiguous_when_mask_matches_twice(self):
        first = _account("One", "GEL", "", "default")
        second = _account("Two", "GEL", "", "default")
        first.iban = PAYMENT_IBAN
        second.iban = "GE30TB0000000000001239GEL"
        first.save(update_fields=["iban"])
        second.save(update_fields=["iban"])
        _import([_message("<pay@gmail.com>", PAYMENT_HTML)])
        self.assertEqual(_transactions("default"), [])
        row = CardSmsMessage.objects.get()
        self.assertEqual(row.status, CardSmsMessage.STATUS_AMBIGUOUS)
        self.assertIsNone(row.transaction_id)

    def test_fetch_keeps_recent_exact_subject(self):
        now = datetime(2026, 10, 27, 4, 0, tzinfo=_TB)
        fake = FakeIMAP(
            {
                b"1": _raw(
                    "<recent@gmail.com>",
                    "Mon, 26 Oct 2026 16:01:16 +0400",
                    "Test",
                    GEL_HTML,
                ),
                b"2": _raw(
                    "<old@gmail.com>",
                    "Mon, 26 Oct 2026 03:00:00 +0400",
                    "Test",
                    GEL_HTML,
                ),
                b"3": _raw(
                    "<other@gmail.com>",
                    "Mon, 26 Oct 2026 16:01:16 +0400",
                    "Testing",
                    GEL_HTML,
                ),
                b"4": _raw("", "Mon, 26 Oct 2026 16:01:16 +0400", "Test", GEL_HTML),
            }
        )
        with patch("crm.card_sms.imaplib.IMAP4_SSL", return_value=fake):
            found = fetch_recent_test_messages(now)
        self.assertEqual([item.message_id for item in found], ["<recent@gmail.com>"])
        self.assertEqual(fake.criteria, ("SINCE", "26-Oct-2026", "SUBJECT", "Test"))
        self.assertIn("Wolt", found[0].body)

    def test_matches_business_and_personal(self):
        _account("Business GEL", "GEL", "3319", "default")
        _account("Personal USD", "USD", "1996", "personal")
        _import(
            [
                _message("<gel@gmail.com>", GEL_HTML),
                _message("<usd@gmail.com>", USD_HTML),
            ]
        )
        business = _transactions("default")
        personal = _transactions("personal")
        self.assertEqual(len(business), 1)
        self.assertEqual(business[0].amount, Decimal("-66.56"))
        self.assertEqual(business[0].kind, FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(business[0].date, date(2026, 10, 26))
        self.assertEqual(business[0].counterparty_name, "Wolt")
        self.assertEqual(business[0].description, "Wolt")
        self.assertEqual(business[0].external_id, "<gel@gmail.com>")
        self.assertEqual(len(personal), 1)
        self.assertEqual(personal[0].amount, Decimal("-50.00"))
        self.assertEqual(personal[0].date, date(2026, 10, 27))
        self.assertEqual(personal[0].counterparty_name, "FACEBK* D4D8PDAQM4>+35315530550 IE")
        gel = CardSmsMessage.objects.get(message_id="<gel@gmail.com>")
        usd = CardSmsMessage.objects.get(message_id="<usd@gmail.com>")
        self.assertEqual(gel.status, CardSmsMessage.STATUS_INSERTED)
        self.assertEqual(gel.finance_db, "default")
        self.assertEqual(gel.transaction_id, business[0].pk)
        self.assertEqual(usd.status, CardSmsMessage.STATUS_INSERTED)
        self.assertEqual(usd.finance_db, "personal")
        self.assertEqual(usd.transaction_id, personal[0].pk)

    def test_same_card_matches_only_sms_currency(self):
        gel_account = _account("GEL card", "GEL", "3319", "default")
        _account("USD card", "USD", "3319", "personal")
        _import([_message("<gel@gmail.com>", GEL_HTML)])
        business = _transactions("default")
        self.assertEqual(len(business), 1)
        self.assertEqual(business[0].account_id, gel_account.pk)
        self.assertEqual(_transactions("personal"), [])

    def test_second_run_does_not_duplicate(self):
        _account("Business GEL", "GEL", "3319", "default")
        messages = [_message("<gel@gmail.com>", GEL_HTML)]
        _import(messages)
        _import(messages)
        self.assertEqual(len(_transactions("default")), 1)
        self.assertEqual(CardSmsMessage.objects.count(), 1)

    def test_ambiguous_when_card_and_currency_match_twice(self):
        _account("One", "GEL", "3319", "default")
        _account("Two", "GEL", "3319,4411", "default")
        _import([_message("<gel@gmail.com>", GEL_HTML)])
        self.assertEqual(_transactions("default"), [])
        row = CardSmsMessage.objects.get()
        self.assertEqual(row.status, CardSmsMessage.STATUS_AMBIGUOUS)
        self.assertIsNone(row.transaction_id)

    def test_account_sms_matches_bog_business_gel(self):
        account = _account("BOG business GEL", "GEL", "", "default")
        _import(
            [
                _message("<out@gmail.com>", GASAVLI_HTML),
                _message("<in@gmail.com>", CHARICXVA_HTML),
            ]
        )
        rows = _transactions("default")
        self.assertEqual(len(rows), 2)
        by_external_id = {row.external_id: row for row in rows}
        expense = by_external_id["<out@gmail.com>"]
        income = by_external_id["<in@gmail.com>"]
        self.assertEqual(expense.account_id, account.pk)
        self.assertEqual(expense.amount, Decimal("-151.20"))
        self.assertEqual(expense.kind, FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(expense.income_type, "")
        self.assertEqual(expense.counterparty_name, "SWEET CHILL")
        self.assertEqual(expense.description, "SWEET CHILL")
        self.assertEqual(expense.date, date(2026, 10, 24))
        self.assertEqual(income.account_id, account.pk)
        self.assertEqual(income.amount, Decimal("325.84"))
        self.assertEqual(income.kind, FinancialTransaction.KIND_INCOME)
        self.assertEqual(income.income_type, FinancialTransaction.INCOME_TRANSFER)
        self.assertEqual(income.counterparty_name, "LTD WISE PAYMENTS")
        self.assertEqual(income.description, "LTD WISE PAYMENTS")
        self.assertEqual(income.date, date(2026, 10, 23))
        self.assertEqual(_transactions("personal"), [])
        stored_expense = CardSmsMessage.objects.get(message_id="<out@gmail.com>")
        stored_income = CardSmsMessage.objects.get(message_id="<in@gmail.com>")
        self.assertEqual(stored_expense.amount, Decimal("151.20"))
        self.assertEqual(stored_expense.kind, CardSmsMessage.KIND_EXPENSE)
        self.assertEqual(stored_expense.status, CardSmsMessage.STATUS_INSERTED)
        self.assertEqual(stored_expense.finance_db, "default")
        self.assertEqual(stored_expense.transaction_id, expense.pk)
        self.assertEqual(stored_income.amount, Decimal("325.84"))
        self.assertEqual(stored_income.kind, CardSmsMessage.KIND_INCOME)
        self.assertEqual(stored_income.status, CardSmsMessage.STATUS_INSERTED)
        self.assertEqual(stored_income.transaction_id, income.pk)

    def test_account_sms_ignores_other_account(self):
        _account("Business GEL", "GEL", "", "default")
        _import([_message("<out@gmail.com>", GASAVLI_HTML)])
        self.assertEqual(_transactions("default"), [])
        self.assertEqual(_transactions("personal"), [])
        row = CardSmsMessage.objects.get()
        self.assertEqual(row.status, CardSmsMessage.STATUS_UNMATCHED)
        self.assertEqual(row.amount, Decimal("151.20"))
        self.assertEqual(row.kind, CardSmsMessage.KIND_EXPENSE)

    def test_unparsed_body_does_not_create_transaction(self):
        _account("Business GEL", "GEL", "3319", "default")
        _import([_message("<plain@gmail.com>", "Hello there")])
        self.assertEqual(_transactions("default"), [])
        row = CardSmsMessage.objects.get()
        self.assertEqual(row.status, CardSmsMessage.STATUS_UNPARSED)

    def test_unmatched_inserts_after_card_is_added(self):
        _import([_message("<gel@gmail.com>", GEL_HTML)])
        self.assertEqual(CardSmsMessage.objects.get().status, CardSmsMessage.STATUS_UNMATCHED)
        self.assertEqual(_transactions("default"), [])
        _account("Business GEL", "GEL", "3319", "default")
        _import([])
        self.assertEqual(len(_transactions("default")), 1)
        self.assertEqual(CardSmsMessage.objects.get().status, CardSmsMessage.STATUS_INSERTED)

    def test_cards_field_keeps_last_four_digits(self):
        account = FinancialAccount(
            name="Card",
            kind=FinancialAccount.KIND_BANK,
            currency="GEL",
            cards="3319, 19",
        )
        with self.assertRaises(ValidationError):
            account.full_clean()
        account.cards = "3319, 1996"
        account.full_clean()
        self.assertEqual(account.cards, "3319,1996")
        account.cards = ""
        account.full_clean()
        self.assertEqual(account.cards, "")

    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_invoices", lambda: None)
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_waybills", lambda: None)
    @patch("crm.management.commands.sync_crm_orders_to_telegram.sync_flowwow_orders")
    @patch("crm.management.commands.sync_crm_orders_to_telegram.import_card_sms")
    def test_sync_command_imports_card_sms(self, mock_import, _flowwow):
        call_command("sync_crm_orders_to_telegram")
        mock_import.assert_called_once_with()
