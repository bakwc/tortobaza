from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from crm.models import FinancialAccount, FinancialTransaction
from crm.paypal_transactions import sync_paypal_transactions
from orders.paypal import list_transactions

INITIATED = "2026-11-22T22:30:00+0000"
TB_DATE = date(2026, 11, 23)
PAYMENT_ID = "TX1|T0006"
FEE_ID = "TX1|T0006|fee"


def _account() -> FinancialAccount:
    return FinancialAccount.objects.create(
        name="PayPal",
        kind=FinancialAccount.KIND_VIRTUAL,
        currency="USD",
    )


def _manual(account: FinancialAccount, amount: str, description: str) -> FinancialTransaction:
    return FinancialTransaction.objects.create(
        account=account,
        date=TB_DATE,
        amount=Decimal(amount),
        kind=FinancialTransaction.KIND_INCOME,
        description=description,
        counterparty_name="Hand",
    )


def _detail(
    amount: str = "100.00",
    fee: str | None = "-3.49",
    currency: str = "USD",
    initiated: str = INITIATED,
) -> dict:
    info = {
        "transaction_id": "TX1",
        "transaction_event_code": "T0006",
        "transaction_initiation_date": initiated,
        "transaction_amount": {"currency_code": currency, "value": amount},
        "transaction_status": "S",
        "transaction_subject": "Cake",
    }
    if fee is not None:
        info["fee_amount"] = {"currency_code": currency, "value": fee}
    return {
        "transaction_info": info,
        "payer_info": {
            "email_address": "ada@example.com",
            "payer_name": {"alternate_full_name": "Ada Lovelace"},
        },
    }


def _token_response() -> Mock:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"access_token": "token"}
    return response


@override_settings(PAYPAL_ENABLED="1")
class SyncPaypalTransactionsTests(TestCase):
    @patch("crm.paypal_transactions.list_transactions")
    def test_creates_payment_and_fee(self, listed):
        account = _account()
        listed.return_value = [_detail()]

        sync_paypal_transactions()

        self.assertEqual(FinancialTransaction.objects.count(), 2)
        payment = FinancialTransaction.objects.get(external_id=PAYMENT_ID)
        self.assertEqual(payment.account, account)
        self.assertEqual(payment.date, TB_DATE)
        self.assertEqual(payment.amount, Decimal("100.00"))
        self.assertEqual(payment.kind, FinancialTransaction.KIND_INCOME)
        self.assertEqual(payment.income_type, FinancialTransaction.INCOME_ONLINE)
        self.assertEqual(payment.expense_type, "")
        self.assertEqual(payment.counterparty_name, "Ada Lovelace")
        self.assertEqual(payment.description, "Cake")
        fee = FinancialTransaction.objects.get(external_id=FEE_ID)
        self.assertEqual(fee.date, TB_DATE)
        self.assertEqual(fee.amount, Decimal("-3.49"))
        self.assertEqual(fee.kind, FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(fee.expense_type, FinancialTransaction.EXPENSE_FEES)
        self.assertEqual(fee.income_type, "")
        self.assertEqual(fee.counterparty_name, "Ada Lovelace")
        self.assertEqual(fee.description, "Cake fee")
        start, end = listed.call_args.args
        self.assertEqual(end - start, timedelta(days=30))

    @patch("crm.paypal_transactions.list_transactions")
    def test_second_call_does_not_duplicate(self, listed):
        _account()
        listed.return_value = [_detail()]

        sync_paypal_transactions()
        sync_paypal_transactions()

        self.assertEqual(FinancialTransaction.objects.count(), 2)

    @patch("crm.paypal_transactions.list_transactions")
    def test_duplicate_in_one_response_is_stored_once(self, listed):
        _account()
        detail = _detail()
        listed.return_value = [detail, detail]

        sync_paypal_transactions()

        self.assertEqual(FinancialTransaction.objects.count(), 2)

    @patch("crm.paypal_transactions.list_transactions")
    def test_manual_same_date_and_amount_is_stamped(self, listed):
        account = _account()
        manual = _manual(account, "100.00", "typed")
        listed.return_value = [_detail()]

        sync_paypal_transactions()

        manual.refresh_from_db()
        self.assertEqual(manual.external_id, PAYMENT_ID)
        self.assertEqual(manual.amount, Decimal("100.00"))
        self.assertEqual(manual.date, TB_DATE)
        self.assertEqual(manual.kind, FinancialTransaction.KIND_INCOME)
        self.assertEqual(manual.description, "typed")
        self.assertEqual(manual.counterparty_name, "Hand")
        self.assertEqual(FinancialTransaction.objects.count(), 2)
        fee = FinancialTransaction.objects.exclude(pk=manual.pk).get()
        self.assertEqual(fee.external_id, FEE_ID)

    @patch("crm.paypal_transactions.list_transactions")
    def test_manual_different_amount_stays(self, listed):
        account = _account()
        manual = _manual(account, "50.00", "typed")
        listed.return_value = [_detail()]

        sync_paypal_transactions()

        manual.refresh_from_db()
        self.assertEqual(manual.external_id, "")
        self.assertEqual(manual.description, "typed")
        self.assertEqual(FinancialTransaction.objects.count(), 3)

    @patch("crm.paypal_transactions.list_transactions")
    def test_two_manuals_same_amount_stamps_the_earlier_one(self, listed):
        account = _account()
        first = _manual(account, "100.00", "first")
        second = _manual(account, "100.00", "second")
        listed.return_value = [_detail()]

        sync_paypal_transactions()

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.external_id, PAYMENT_ID)
        self.assertEqual(first.description, "first")
        self.assertEqual(second.external_id, "")
        self.assertEqual(second.description, "second")
        self.assertEqual(FinancialTransaction.objects.count(), 3)

    @patch("crm.paypal_transactions.list_transactions")
    def test_negative_amount_is_expense(self, listed):
        _account()
        listed.return_value = [_detail(amount="-40.00", fee=None)]

        sync_paypal_transactions()

        payment = FinancialTransaction.objects.get()
        self.assertEqual(payment.amount, Decimal("-40.00"))
        self.assertEqual(payment.kind, FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(payment.income_type, "")
        self.assertEqual(payment.expense_type, "")

    @patch("crm.paypal_transactions.list_transactions")
    def test_positive_fee_is_income(self, listed):
        _account()
        listed.return_value = [_detail(amount="0.00", fee="1.20")]

        sync_paypal_transactions()

        fee = FinancialTransaction.objects.get()
        self.assertEqual(fee.external_id, FEE_ID)
        self.assertEqual(fee.amount, Decimal("1.20"))
        self.assertEqual(fee.kind, FinancialTransaction.KIND_INCOME)
        self.assertEqual(fee.income_type, "")
        self.assertEqual(fee.expense_type, "")

    @patch("crm.paypal_transactions.list_transactions")
    def test_currency_mismatch_raises(self, listed):
        _account()
        listed.return_value = [_detail(currency="EUR")]

        with self.assertRaises(ValueError):
            sync_paypal_transactions()

        self.assertEqual(FinancialTransaction.objects.count(), 0)

    @patch("crm.paypal_transactions.list_transactions")
    def test_raises_when_account_missing(self, listed):
        with self.assertRaises(FinancialAccount.DoesNotExist):
            sync_paypal_transactions()

        listed.assert_not_called()

    def test_raises_when_account_matched_more_than_once(self):
        _account()
        _account()

        with self.assertRaises(ValueError):
            sync_paypal_transactions()

    @override_settings(PAYPAL_ENABLED="")
    @patch("crm.paypal_transactions.list_transactions")
    def test_disabled_does_not_call_paypal(self, listed):
        _account()

        sync_paypal_transactions()

        listed.assert_not_called()
        self.assertEqual(FinancialTransaction.objects.count(), 0)


@override_settings(
    PAYPAL_API_URL="https://api-m.paypal.com",
    PAYPAL_CLIENT_ID="id",
    PAYPAL_CLIENT_SECRET="secret",
)
class ListTransactionsTests(TestCase):
    @patch("orders.paypal.requests.get")
    @patch("orders.paypal.requests.post")
    def test_pages_and_date_params(self, post, get):
        post.return_value = _token_response()
        pages = {
            1: {
                "transaction_details": [{"transaction_info": {"transaction_id": "A"}}],
                "total_pages": 2,
            },
            2: {
                "transaction_details": [{"transaction_info": {"transaction_id": "B"}}],
                "total_pages": 2,
            },
        }

        def fetch(url, **kwargs):
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = pages[kwargs["params"]["page"]]
            return response

        get.side_effect = fetch
        start = datetime(2026, 10, 1, 12, 30, 45, tzinfo=timezone.utc)
        end = datetime(2026, 11, 1, 8, 0, 1, tzinfo=timezone.utc)

        rows = list_transactions(start, end)

        self.assertEqual(
            [row["transaction_info"]["transaction_id"] for row in rows],
            ["A", "B"],
        )
        self.assertEqual(
            get.call_args_list[0].args[0],
            "https://api-m.paypal.com/v1/reporting/transactions",
        )
        params = get.call_args_list[0].kwargs["params"]
        self.assertEqual(params["start_date"], "2026-10-01T12:30:45Z")
        self.assertEqual(params["end_date"], "2026-11-01T08:00:01Z")
        self.assertEqual(params["transaction_status"], "S")
        self.assertEqual(params["fields"], "all")
        self.assertEqual(params["page_size"], 500)
        self.assertEqual(params["page"], 1)
        self.assertEqual(
            get.call_args_list[0].kwargs["headers"]["Authorization"],
            "Bearer token",
        )
        self.assertEqual(get.call_args_list[1].kwargs["params"]["page"], 2)
        self.assertEqual(post.call_args.kwargs["data"]["grant_type"], "client_credentials")
        self.assertNotIn("scope", post.call_args.kwargs["data"])
