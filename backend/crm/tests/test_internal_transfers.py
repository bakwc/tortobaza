from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from crm.internal_transfers import BOG_BANK_NAME, sync_internal_transfers
from crm.models import FinancialAccount, FinancialTransaction

BOG_IBAN = "GE94BG0000000612361573"
TBC_IBAN = "GE07TB7154245068100036"
LIBERTY_IBAN = "GE53LB0112183991465000"
FOREIGN_IBAN = "GE25BG0000000609431766"
DAY = date(2026, 9, 6)


def _account(name: str, iban: str, currency: str, bank_name: str) -> FinancialAccount:
    return FinancialAccount.objects.create(
        name=name,
        kind=FinancialAccount.KIND_BANK,
        bank_name=bank_name,
        iban=iban,
        currency=currency,
    )


def _tx(
    account: FinancialAccount,
    day: date,
    amount: Decimal,
    kind: str,
    counterparty_iban: str,
    external_id: str,
    description: str,
) -> FinancialTransaction:
    return FinancialTransaction.objects.create(
        account=account,
        date=day,
        amount=amount,
        kind=kind,
        counterparty_iban=counterparty_iban,
        description=description,
        external_id=external_id,
    )


class SyncInternalTransfersTests(TestCase):
    def test_matches_bog_gel_to_tbc_across_iban_suffix(self):
        bog = _account("BOG business GEL", f"{BOG_IBAN}GEL", "GEL", BOG_BANK_NAME)
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        outgoing = _tx(
            bog,
            DAY,
            Decimal("-430.00"),
            FinancialTransaction.KIND_EXPENSE,
            TBC_IBAN,
            "124945756136",
            "BONUS",
        )
        incoming = _tx(
            tbc,
            DAY,
            Decimal("430.00"),
            FinancialTransaction.KIND_INCOME,
            BOG_IBAN,
            "tbc-430",
            "BONUS",
        )

        sync_internal_transfers()

        outgoing.refresh_from_db()
        incoming.refresh_from_db()
        self.assertEqual(outgoing.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(incoming.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(outgoing.matched_transaction_id, incoming.pk)
        self.assertEqual(incoming.matched_transaction_id, outgoing.pk)

    def test_matches_liberty_to_tbc_one_day_later(self):
        liberty = _account("Liberty", LIBERTY_IBAN, "GEL", "Liberty Bank")
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        outgoing = _tx(
            liberty,
            DAY,
            Decimal("-740.00"),
            FinancialTransaction.KIND_EXPENSE,
            TBC_IBAN,
            "liberty-740",
            "bonus",
        )
        incoming = _tx(
            tbc,
            DAY + timedelta(days=1),
            Decimal("740.00"),
            FinancialTransaction.KIND_INCOME,
            LIBERTY_IBAN,
            "tbc-740",
            "bonus",
        )

        sync_internal_transfers()

        outgoing.refresh_from_db()
        incoming.refresh_from_db()
        self.assertEqual(outgoing.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(incoming.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(outgoing.matched_transaction_id, incoming.pk)
        self.assertEqual(incoming.matched_transaction_id, outgoing.pk)

    def test_marks_transfer_without_counterparty_row(self):
        liberty = _account("Liberty", LIBERTY_IBAN, "GEL", "Liberty Bank")
        _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        outgoing = _tx(
            liberty,
            DAY,
            Decimal("-390.00"),
            FinancialTransaction.KIND_EXPENSE,
            TBC_IBAN,
            "liberty-390",
            "dividents",
        )

        sync_internal_transfers()

        outgoing.refresh_from_db()
        self.assertEqual(outgoing.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertIsNone(outgoing.matched_transaction_id)

    def test_bog_fee_sibling_stays_expense(self):
        bog = _account("BOG business GEL", f"{BOG_IBAN}GEL", "GEL", BOG_BANK_NAME)
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        outgoing = _tx(
            bog,
            DAY,
            Decimal("-430.00"),
            FinancialTransaction.KIND_EXPENSE,
            TBC_IBAN,
            "124945756136",
            "BONUS",
        )
        fee = _tx(
            bog,
            DAY,
            Decimal("-1.00"),
            FinancialTransaction.KIND_EXPENSE,
            TBC_IBAN,
            "124945756137",
            "BONUS",
        )
        incoming = _tx(
            tbc,
            DAY,
            Decimal("430.00"),
            FinancialTransaction.KIND_INCOME,
            BOG_IBAN,
            "tbc-430",
            "BONUS",
        )

        sync_internal_transfers()
        sync_internal_transfers()

        outgoing.refresh_from_db()
        fee.refresh_from_db()
        incoming.refresh_from_db()
        self.assertEqual(outgoing.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(outgoing.matched_transaction_id, incoming.pk)
        self.assertEqual(fee.kind, FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(fee.expense_type, FinancialTransaction.EXPENSE_FEES)
        self.assertIsNone(fee.matched_transaction_id)
        self.assertEqual(incoming.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(incoming.matched_transaction_id, outgoing.pk)

    def test_ignores_own_iban_and_foreign_iban(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        conversion = _tx(
            tbc,
            DAY,
            Decimal("10.90"),
            FinancialTransaction.KIND_INCOME,
            TBC_IBAN,
            "conversion",
            "კონვერტაცია",
        )
        foreign = _tx(
            tbc,
            DAY,
            Decimal("-1350.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "foreign",
            "Bonus",
        )

        sync_internal_transfers()

        conversion.refresh_from_db()
        foreign.refresh_from_db()
        self.assertEqual(conversion.kind, FinancialTransaction.KIND_INCOME)
        self.assertIsNone(conversion.matched_transaction_id)
        self.assertEqual(foreign.kind, FinancialTransaction.KIND_EXPENSE)
        self.assertIsNone(foreign.matched_transaction_id)

    def test_does_not_pair_when_two_incomings_match(self):
        bog = _account("BOG business GEL", f"{BOG_IBAN}GEL", "GEL", BOG_BANK_NAME)
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        outgoing = _tx(
            bog,
            DAY,
            Decimal("-100.00"),
            FinancialTransaction.KIND_EXPENSE,
            TBC_IBAN,
            "out",
            "BONUS",
        )
        first = _tx(
            tbc,
            DAY,
            Decimal("100.00"),
            FinancialTransaction.KIND_INCOME,
            BOG_IBAN,
            "in-1",
            "BONUS",
        )
        second = _tx(
            tbc,
            DAY + timedelta(days=1),
            Decimal("100.00"),
            FinancialTransaction.KIND_INCOME,
            BOG_IBAN,
            "in-2",
            "BONUS",
        )

        sync_internal_transfers()

        outgoing.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(outgoing.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(first.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(second.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertIsNone(outgoing.matched_transaction_id)
        self.assertIsNone(first.matched_transaction_id)
        self.assertIsNone(second.matched_transaction_id)

    def test_picks_account_by_currency(self):
        bog_usd = _account("BOG business USD", f"{BOG_IBAN}USD", "USD", BOG_BANK_NAME)
        _account("BOG business GEL", f"{BOG_IBAN}GEL", "GEL", BOG_BANK_NAME)
        other = _account("Other USD", "GE99TB0000000000000001", "USD", "TBC")
        outgoing = _tx(
            other,
            DAY,
            Decimal("-10.00"),
            FinancialTransaction.KIND_EXPENSE,
            BOG_IBAN,
            "out-usd",
            "transfer",
        )
        incoming = _tx(
            bog_usd,
            DAY,
            Decimal("10.00"),
            FinancialTransaction.KIND_INCOME,
            "GE99TB0000000000000001",
            "in-usd",
            "transfer",
        )

        sync_internal_transfers()

        outgoing.refresh_from_db()
        incoming.refresh_from_db()
        self.assertEqual(outgoing.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(incoming.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(outgoing.matched_transaction_id, incoming.pk)
        self.assertEqual(incoming.matched_transaction_id, outgoing.pk)
