from datetime import date, datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from crm.bog_statement import import_bog_statement
from crm.card_sms import _match_row
from crm.models import CardSmsMessage, FinancialAccount, FinancialTransaction
from crm.tests.test_bog_statement import GEL_IBAN, _account, _excel_serial, _statement

MESSAGE_ID = "<sms@test>"
OPERATION_ID = "701"


def _sms(
    account: FinancialAccount,
    when: date,
    message_id: str,
) -> tuple[FinancialTransaction, CardSmsMessage]:
    tx = FinancialTransaction.objects.create(
        account=account,
        date=when,
        amount=Decimal("-5.00"),
        kind=FinancialTransaction.KIND_EXPENSE,
        counterparty_name="Wolt",
        description="Wolt",
        external_id=message_id,
        expense_type=FinancialTransaction.EXPENSE_PRODUCTS,
    )
    message = CardSmsMessage.objects.create(
        message_id=message_id,
        received_at=timezone.now(),
        raw_body=message_id,
        card_last4="3319",
        currency=account.currency,
        amount=Decimal("5.00"),
        merchant="Wolt",
        sms_date=when,
        status=CardSmsMessage.STATUS_INSERTED,
        finance_db="default",
        transaction_id=tx.pk,
    )
    return tx, message


def _expense_row(operation_id: str, when: datetime) -> dict:
    return {
        "Date": _excel_serial(when),
        "Account N": GEL_IBAN,
        "Debit": 5,
        "Credit": None,
        "Entry Comment": "Card purchase",
        "Operation ID": operation_id,
        "Sender Name": "INDIVIDUAL ENTREPRENEUR FILIPP BAKANOV",
        "Sender Account N": GEL_IBAN,
        "Recipient Name": "Shop",
        "Recipient Account N": "GE00TEST",
        "Nomination": "Cake stuff",
        "Amount": -5,
    }


class SmsStatementMergeTests(TestCase):
    databases = {"default", "personal"}

    def test_merges_sms_within_one_day(self):
        account = _account(GEL_IBAN, "GEL", "SWEET CHILL")
        tx, message = _sms(account, date(2026, 7, 9), MESSAGE_ID)
        result = import_bog_statement(_statement([_expense_row(OPERATION_ID, datetime(2026, 7, 10))]))
        self.assertEqual(result.error, "")
        self.assertEqual(result.created, 0)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(FinancialTransaction.objects.count(), 1)
        tx.refresh_from_db()
        self.assertEqual(tx.pk, message.transaction_id)
        self.assertEqual(tx.date, date(2026, 7, 10))
        self.assertEqual(tx.amount, Decimal("-5.00"))
        self.assertEqual(tx.kind, FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(tx.income_type, FinancialTransaction.INCOME_TRANSFER)
        self.assertEqual(tx.counterparty_name, "Shop")
        self.assertEqual(tx.counterparty_iban, "GE00TEST")
        self.assertEqual(tx.description, "Cake stuff")
        self.assertEqual(tx.external_id, OPERATION_ID)
        self.assertEqual(tx.expense_type, FinancialTransaction.EXPENSE_PRODUCTS)
        message.refresh_from_db()
        self.assertEqual(message.transaction_id, tx.pk)

    def test_two_day_gap_creates_new_transaction(self):
        account = _account(GEL_IBAN, "GEL", "SWEET CHILL")
        tx, _message = _sms(account, date(2026, 7, 8), MESSAGE_ID)
        result = import_bog_statement(_statement([_expense_row(OPERATION_ID, datetime(2026, 7, 10))]))
        self.assertEqual(result.error, "")
        self.assertEqual(result.created, 1)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(FinancialTransaction.objects.count(), 2)
        tx.refresh_from_db()
        self.assertEqual(tx.external_id, MESSAGE_ID)
        self.assertEqual(tx.description, "Wolt")
        created = FinancialTransaction.objects.get(external_id=OPERATION_ID)
        self.assertNotEqual(created.pk, tx.pk)

    def test_closest_sms_wins(self):
        account = _account(GEL_IBAN, "GEL", "SWEET CHILL")
        earlier, _earlier_message = _sms(account, date(2026, 7, 9), "<earlier@test>")
        closest, _closest_message = _sms(account, date(2026, 7, 10), "<closest@test>")
        result = import_bog_statement(_statement([_expense_row(OPERATION_ID, datetime(2026, 7, 10))]))
        self.assertEqual(result.error, "")
        self.assertEqual(result.created, 0)
        self.assertEqual(result.skipped, 1)
        earlier.refresh_from_db()
        closest.refresh_from_db()
        self.assertEqual(earlier.external_id, "<earlier@test>")
        self.assertEqual(closest.external_id, OPERATION_ID)
        self.assertEqual(closest.description, "Cake stuff")

    def test_equal_date_uses_smaller_id(self):
        account = _account(GEL_IBAN, "GEL", "SWEET CHILL")
        first, _first_message = _sms(account, date(2026, 7, 10), "<first@test>")
        second, _second_message = _sms(account, date(2026, 7, 10), "<second@test>")
        result = import_bog_statement(_statement([_expense_row(OPERATION_ID, datetime(2026, 7, 10))]))
        self.assertEqual(result.error, "")
        self.assertEqual(result.created, 0)
        self.assertEqual(result.skipped, 1)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertLess(first.pk, second.pk)
        self.assertEqual(first.external_id, OPERATION_ID)
        self.assertEqual(second.external_id, "<second@test>")

    def test_reimport_skips_merged_transaction(self):
        account = _account(GEL_IBAN, "GEL", "SWEET CHILL")
        _sms(account, date(2026, 7, 9), MESSAGE_ID)
        statement = _statement([_expense_row(OPERATION_ID, datetime(2026, 7, 10))])
        import_bog_statement(statement)
        statement.seek(0)
        again = import_bog_statement(statement)
        self.assertEqual(again.error, "")
        self.assertEqual(again.created, 0)
        self.assertEqual(again.skipped, 1)
        self.assertEqual(FinancialTransaction.objects.count(), 1)
        tx = FinancialTransaction.objects.get()
        self.assertEqual(tx.external_id, OPERATION_ID)
        self.assertEqual(tx.description, "Cake stuff")

    def test_other_account_is_not_merged(self):
        _account(GEL_IBAN, "GEL", "SWEET CHILL")
        other = FinancialAccount.objects.create(
            name="Other",
            kind=FinancialAccount.KIND_BANK,
            iban="GE00OTHER",
            currency="GEL",
        )
        tx, _message = _sms(other, date(2026, 7, 10), MESSAGE_ID)
        result = import_bog_statement(_statement([_expense_row(OPERATION_ID, datetime(2026, 7, 10))]))
        self.assertEqual(result.error, "")
        self.assertEqual(result.created, 1)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(FinancialTransaction.objects.count(), 2)
        tx.refresh_from_db()
        self.assertEqual(tx.external_id, MESSAGE_ID)
        self.assertEqual(tx.account, other)

    def test_repeat_sms_after_merge_does_not_create(self):
        account = _account(GEL_IBAN, "GEL", "SWEET CHILL")
        account.cards = "3319"
        account.save(update_fields=["cards"])
        tx, message = _sms(account, date(2026, 7, 9), MESSAGE_ID)
        import_bog_statement(_statement([_expense_row(OPERATION_ID, datetime(2026, 7, 10))]))
        message.status = CardSmsMessage.STATUS_UNMATCHED
        message.save(update_fields=["status"])
        _match_row(message)
        self.assertEqual(FinancialTransaction.objects.count(), 1)
        message.refresh_from_db()
        tx.refresh_from_db()
        self.assertEqual(message.transaction_id, tx.pk)
        self.assertEqual(message.status, CardSmsMessage.STATUS_INSERTED)
        self.assertEqual(tx.external_id, OPERATION_ID)
        self.assertEqual(tx.description, "Cake stuff")
        self.assertEqual(tx.counterparty_name, "Shop")
        self.assertEqual(tx.date, date(2026, 7, 10))
