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

    def test_pairs_tbc_atm_withdrawal_with_cash(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        cash = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        withdrawal = _tx(
            tbc,
            DAY,
            Decimal("-1000.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-1000",
            "ATM CASH wallet - ATM TBC-1075 (RECAN), 1000.00 GEL",
        )

        sync_internal_transfers()

        withdrawal.refresh_from_db()
        incoming = FinancialTransaction.objects.get(account=cash)
        self.assertEqual(withdrawal.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(withdrawal.matched_transaction_id, incoming.pk)
        self.assertEqual(incoming.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(incoming.amount, Decimal("1000.00"))
        self.assertEqual(incoming.date, DAY)
        self.assertEqual(incoming.description, withdrawal.description)
        self.assertEqual(incoming.external_id, withdrawal.external_id)
        self.assertEqual(incoming.matched_transaction_id, withdrawal.pk)

    def test_second_sync_does_not_duplicate_atm_cash(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        _tx(
            tbc,
            DAY,
            Decimal("-800.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-800",
            "ATM CASH wallet - ATM TBC-1075 (RECAN), 800.00 GEL",
        )

        sync_internal_transfers()
        sync_internal_transfers()

        self.assertEqual(FinancialTransaction.objects.count(), 2)

    def test_leaves_tbc_pos_expense(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        expense = _tx(
            tbc,
            DAY,
            Decimal("-4.70"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "pos",
            "POS - Vip Pay*YANDEX.GO, 4.70 GEL",
        )

        sync_internal_transfers()

        expense.refresh_from_db()
        self.assertEqual(expense.kind, FinancialTransaction.KIND_EXPENSE)
        self.assertIsNone(expense.matched_transaction_id)
        self.assertEqual(FinancialTransaction.objects.filter(account__kind=FinancialAccount.KIND_CASH).count(), 0)

    def test_raises_when_cash_account_missing(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        _tx(
            tbc,
            DAY,
            Decimal("-60.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-60",
            "ATM CASH wallet - ATM TBC-681, 60.00 GEL",
        )

        with self.assertRaises(FinancialAccount.DoesNotExist):
            sync_internal_transfers()

    def test_links_existing_cash_transfer_on_exact_amount(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        cash = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        withdrawal = _tx(
            tbc,
            DAY,
            Decimal("-1000.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-1000",
            "ATM CASH wallet - ATM TBC-1075 (RECAN), 1000.00 GEL",
        )
        counted = _tx(
            cash,
            DAY,
            Decimal("1000.00"),
            FinancialTransaction.KIND_TRANSFER,
            "",
            "cash-1000",
            "counted",
        )

        sync_internal_transfers()

        withdrawal.refresh_from_db()
        counted.refresh_from_db()
        self.assertEqual(withdrawal.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(withdrawal.matched_transaction_id, counted.pk)
        self.assertEqual(counted.matched_transaction_id, withdrawal.pk)
        self.assertEqual(counted.amount, Decimal("1000.00"))
        self.assertEqual(counted.description, "counted")
        self.assertEqual(FinancialTransaction.objects.count(), 2)
        self.assertEqual(
            FinancialTransaction.objects.filter(kind=FinancialTransaction.KIND_EXPENSE).count(),
            0,
        )

    def test_links_cash_within_one_percent_and_creates_fee(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        cash = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        withdrawal = _tx(
            tbc,
            DAY,
            Decimal("-1502.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-1502",
            "ATM CASH wallet - ATM TBC-1075 (RECAN), 1502.00 GEL",
        )
        counted = _tx(
            cash,
            DAY,
            Decimal("1500.00"),
            FinancialTransaction.KIND_TRANSFER,
            "",
            "cash-1500",
            "counted",
        )

        sync_internal_transfers()

        withdrawal.refresh_from_db()
        counted.refresh_from_db()
        fee = FinancialTransaction.objects.get(kind=FinancialTransaction.KIND_EXPENSE)
        self.assertEqual(withdrawal.kind, FinancialTransaction.KIND_TRANSFER)
        self.assertEqual(withdrawal.amount, Decimal("-1502.00"))
        self.assertEqual(withdrawal.matched_transaction_id, counted.pk)
        self.assertEqual(counted.matched_transaction_id, withdrawal.pk)
        self.assertEqual(counted.amount, Decimal("1500.00"))
        self.assertEqual(counted.description, "counted")
        self.assertEqual(fee.account_id, cash.pk)
        self.assertEqual(fee.date, DAY)
        self.assertEqual(fee.amount, Decimal("-2.00"))
        self.assertEqual(fee.expense_type, FinancialTransaction.EXPENSE_FEES)
        self.assertEqual(fee.description, "Комиссия за снятие")
        self.assertEqual(fee.external_id, f"atm-fee:{withdrawal.pk}")
        self.assertIsNone(fee.matched_transaction_id)
        self.assertEqual(FinancialTransaction.objects.count(), 3)

    def test_links_larger_cash_within_one_percent_without_fee(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        cash = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        withdrawal = _tx(
            tbc,
            DAY,
            Decimal("-1500.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-1500",
            "ATM CASH wallet - ATM TBC-1075 (RECAN), 1500.00 GEL",
        )
        counted = _tx(
            cash,
            DAY,
            Decimal("1510.00"),
            FinancialTransaction.KIND_TRANSFER,
            "",
            "cash-1510",
            "counted",
        )

        sync_internal_transfers()

        withdrawal.refresh_from_db()
        counted.refresh_from_db()
        self.assertEqual(withdrawal.matched_transaction_id, counted.pk)
        self.assertEqual(counted.matched_transaction_id, withdrawal.pk)
        self.assertEqual(counted.amount, Decimal("1510.00"))
        self.assertEqual(FinancialTransaction.objects.count(), 2)

    def test_links_cash_transfer_three_days_later(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        cash = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        withdrawal = _tx(
            tbc,
            DAY,
            Decimal("-800.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-800",
            "ATM CASH wallet - ATM TBC-1075 (RECAN), 800.00 GEL",
        )
        counted = _tx(
            cash,
            DAY + timedelta(days=3),
            Decimal("800.00"),
            FinancialTransaction.KIND_TRANSFER,
            "",
            "cash-800",
            "counted",
        )

        sync_internal_transfers()

        withdrawal.refresh_from_db()
        counted.refresh_from_db()
        self.assertEqual(withdrawal.matched_transaction_id, counted.pk)
        self.assertEqual(counted.matched_transaction_id, withdrawal.pk)
        self.assertEqual(FinancialTransaction.objects.count(), 2)

    def test_creates_pair_when_cash_is_four_days_later(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        cash = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        withdrawal = _tx(
            tbc,
            DAY,
            Decimal("-800.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-800",
            "ATM CASH wallet - ATM TBC-1075 (RECAN), 800.00 GEL",
        )
        counted = _tx(
            cash,
            DAY + timedelta(days=4),
            Decimal("800.00"),
            FinancialTransaction.KIND_TRANSFER,
            "",
            "cash-800",
            "counted",
        )

        sync_internal_transfers()

        withdrawal.refresh_from_db()
        counted.refresh_from_db()
        created = FinancialTransaction.objects.get(
            account=cash,
            external_id=withdrawal.external_id,
        )
        self.assertIsNone(counted.matched_transaction_id)
        self.assertEqual(withdrawal.matched_transaction_id, created.pk)
        self.assertEqual(created.amount, Decimal("800.00"))
        self.assertEqual(created.date, DAY)

    def test_creates_pair_when_cash_is_before_withdrawal(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        cash = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        withdrawal = _tx(
            tbc,
            DAY,
            Decimal("-800.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-800",
            "ATM CASH wallet - ATM TBC-1075 (RECAN), 800.00 GEL",
        )
        counted = _tx(
            cash,
            DAY - timedelta(days=1),
            Decimal("800.00"),
            FinancialTransaction.KIND_TRANSFER,
            "",
            "cash-800",
            "counted",
        )

        sync_internal_transfers()

        withdrawal.refresh_from_db()
        counted.refresh_from_db()
        created = FinancialTransaction.objects.get(
            account=cash,
            external_id=withdrawal.external_id,
        )
        self.assertIsNone(counted.matched_transaction_id)
        self.assertEqual(withdrawal.matched_transaction_id, created.pk)
        self.assertEqual(created.amount, Decimal("800.00"))

    def test_creates_pair_when_difference_exceeds_one_percent(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        cash = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        withdrawal = _tx(
            tbc,
            DAY,
            Decimal("-1000.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-1000",
            "ATM CASH wallet - ATM TBC-1075 (RECAN), 1000.00 GEL",
        )
        counted = _tx(
            cash,
            DAY,
            Decimal("980.00"),
            FinancialTransaction.KIND_TRANSFER,
            "",
            "cash-980",
            "counted",
        )

        sync_internal_transfers()

        withdrawal.refresh_from_db()
        counted.refresh_from_db()
        created = FinancialTransaction.objects.get(
            account=cash,
            external_id=withdrawal.external_id,
        )
        self.assertIsNone(counted.matched_transaction_id)
        self.assertEqual(withdrawal.matched_transaction_id, created.pk)
        self.assertEqual(created.amount, Decimal("1000.00"))
        self.assertEqual(
            FinancialTransaction.objects.filter(kind=FinancialTransaction.KIND_EXPENSE).count(),
            0,
        )

    def test_ignores_paired_cash_transfer_and_non_transfer(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        cash = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        other = _tx(
            tbc,
            DAY,
            Decimal("-1000.00"),
            FinancialTransaction.KIND_TRANSFER,
            "",
            "manual-out",
            "manual",
        )
        paired = _tx(
            cash,
            DAY,
            Decimal("1000.00"),
            FinancialTransaction.KIND_TRANSFER,
            "",
            "cash-paired",
            "already paired",
        )
        paired.matched_transaction = other
        other.matched_transaction = paired
        paired.save(update_fields=["matched_transaction"])
        other.save(update_fields=["matched_transaction"])
        income = _tx(
            cash,
            DAY,
            Decimal("1000.00"),
            FinancialTransaction.KIND_INCOME,
            "",
            "cash-income",
            "sale",
        )
        withdrawal = _tx(
            tbc,
            DAY,
            Decimal("-1000.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-1000",
            "ATM CASH wallet - ATM TBC-1075 (RECAN), 1000.00 GEL",
        )

        sync_internal_transfers()

        withdrawal.refresh_from_db()
        paired.refresh_from_db()
        income.refresh_from_db()
        created = FinancialTransaction.objects.get(
            account=cash,
            external_id=withdrawal.external_id,
        )
        self.assertEqual(paired.matched_transaction_id, other.pk)
        self.assertEqual(income.kind, FinancialTransaction.KIND_INCOME)
        self.assertIsNone(income.matched_transaction_id)
        self.assertEqual(withdrawal.matched_transaction_id, created.pk)
        self.assertEqual(created.amount, Decimal("1000.00"))

    def test_exact_cash_match_wins_over_nearby_withdrawal(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        cash = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        exact = _tx(
            tbc,
            DAY,
            Decimal("-1500.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-1500",
            "ATM CASH wallet - exact, 1500.00 GEL",
        )
        nearby = _tx(
            tbc,
            DAY,
            Decimal("-1502.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-1502",
            "ATM CASH wallet - nearby, 1502.00 GEL",
        )
        counted = _tx(
            cash,
            DAY,
            Decimal("1500.00"),
            FinancialTransaction.KIND_TRANSFER,
            "",
            "cash-1500",
            "counted",
        )

        sync_internal_transfers()

        exact.refresh_from_db()
        nearby.refresh_from_db()
        counted.refresh_from_db()
        created = FinancialTransaction.objects.get(
            account=cash,
            external_id=nearby.external_id,
        )
        self.assertEqual(exact.matched_transaction_id, counted.pk)
        self.assertEqual(counted.matched_transaction_id, exact.pk)
        self.assertEqual(counted.amount, Decimal("1500.00"))
        self.assertEqual(nearby.matched_transaction_id, created.pk)
        self.assertEqual(created.amount, Decimal("1502.00"))
        self.assertEqual(
            FinancialTransaction.objects.filter(kind=FinancialTransaction.KIND_EXPENSE).count(),
            0,
        )

    def test_second_sync_does_not_duplicate_atm_fee(self):
        tbc = _account("TBC Daria", TBC_IBAN, "GEL", "TBC")
        cash = FinancialAccount.objects.create(name="Cash", kind=FinancialAccount.KIND_CASH)
        _tx(
            tbc,
            DAY,
            Decimal("-1502.00"),
            FinancialTransaction.KIND_EXPENSE,
            FOREIGN_IBAN,
            "atm-1502",
            "ATM CASH wallet - ATM TBC-1075 (RECAN), 1502.00 GEL",
        )
        _tx(
            cash,
            DAY,
            Decimal("1500.00"),
            FinancialTransaction.KIND_TRANSFER,
            "",
            "cash-1500",
            "counted",
        )

        sync_internal_transfers()
        sync_internal_transfers()

        self.assertEqual(FinancialTransaction.objects.count(), 3)
        self.assertEqual(
            FinancialTransaction.objects.filter(
                kind=FinancialTransaction.KIND_EXPENSE,
                expense_type=FinancialTransaction.EXPENSE_FEES,
            ).count(),
            1,
        )
