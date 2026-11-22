from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from audit.record import record_created, record_updates
from audit.snapshot import snapshot_fields
from crm.models import FinancialAccount, FinancialTransaction
from crm.transaction_rules import assign_expense_types
from orders.paypal import list_transactions, paypal_enabled
from tortobaza.finance_db import current_finance_db

ACCOUNT_NAME = "PayPal"
WINDOW = timedelta(days=30)
_TB = ZoneInfo("Asia/Tbilisi")


@dataclass
class PaypalRow:
    date: date
    amount: Decimal
    kind: str
    income_type: str
    expense_type: str
    counterparty_name: str
    description: str
    external_id: str


def sync_paypal_transactions() -> None:
    if not paypal_enabled():
        return
    account = _paypal_account()
    now = timezone.now()
    details = list_transactions(now - WINDOW, now)
    rows = _rows(details, account.currency)
    with transaction.atomic(using=current_finance_db()):
        existing = set(
            FinancialTransaction.objects.filter(
                account=account,
                external_id__in=[row.external_id for row in rows],
            ).values_list("external_id", flat=True)
        )
        pending: list[PaypalRow] = []
        for row in rows:
            if row.external_id in existing:
                continue
            existing.add(row.external_id)
            pending.append(row)
        manuals = _manuals(account, pending)
        to_create: list[FinancialTransaction] = []
        to_update: list[FinancialTransaction] = []
        updates: list[tuple[FinancialTransaction, dict]] = []
        for row in pending:
            bucket = manuals.get((row.date, row.amount))
            if bucket:
                tx = bucket.pop(0)
                before = snapshot_fields(tx)
                tx.external_id = row.external_id
                to_update.append(tx)
                updates.append((tx, before))
                continue
            to_create.append(
                FinancialTransaction(
                    account=account,
                    date=row.date,
                    amount=row.amount,
                    kind=row.kind,
                    income_type=row.income_type,
                    expense_type=row.expense_type,
                    counterparty_name=row.counterparty_name,
                    description=row.description,
                    external_id=row.external_id,
                )
            )
        assign_expense_types(to_create)
        FinancialTransaction.objects.bulk_create(to_create)
        record_created(to_create)
        if to_update:
            FinancialTransaction.objects.bulk_update(to_update, ["external_id"])
            record_updates(updates)


def _paypal_account() -> FinancialAccount:
    accounts = list(FinancialAccount.objects.filter(name=ACCOUNT_NAME))
    if len(accounts) == 0:
        raise FinancialAccount.DoesNotExist
    if len(accounts) > 1:
        raise ValueError("PayPal account matched more than once")
    return accounts[0]


def _manuals(
    account: FinancialAccount,
    pending: list[PaypalRow],
) -> dict[tuple[date, Decimal], list[FinancialTransaction]]:
    if len(pending) == 0:
        return {}
    grouped: dict[tuple[date, Decimal], list[FinancialTransaction]] = {}
    queryset = FinancialTransaction.objects.filter(
        account=account,
        external_id="",
        date__in=[row.date for row in pending],
        amount__in=[row.amount for row in pending],
    ).order_by("pk")
    for tx in queryset:
        grouped.setdefault((tx.date, tx.amount), []).append(tx)
    return grouped


def _rows(details: list[dict], currency: str) -> list[PaypalRow]:
    rows: list[PaypalRow] = []
    for detail in details:
        info = detail["transaction_info"]
        when = _tbilisi_date(info["transaction_initiation_date"])
        counterparty = _counterparty(detail)
        description = _description(info)
        external_id = f"{info['transaction_id']}|{info['transaction_event_code']}"
        amount = _amount(info["transaction_amount"], currency)
        if amount != 0:
            kind, income_type, expense_type = _payment_kind(amount)
            rows.append(
                PaypalRow(
                    date=when,
                    amount=amount,
                    kind=kind,
                    income_type=income_type,
                    expense_type=expense_type,
                    counterparty_name=counterparty,
                    description=description,
                    external_id=external_id,
                )
            )
        if "fee_amount" in info:
            fee = _amount(info["fee_amount"], currency)
            if fee != 0:
                kind, income_type, expense_type = _fee_kind(fee)
                rows.append(
                    PaypalRow(
                        date=when,
                        amount=fee,
                        kind=kind,
                        income_type=income_type,
                        expense_type=expense_type,
                        counterparty_name=counterparty,
                        description=f"{description} fee",
                        external_id=f"{external_id}|fee",
                    )
                )
    return rows


def _payment_kind(amount: Decimal) -> tuple[str, str, str]:
    if amount > 0:
        return FinancialTransaction.KIND_INCOME, FinancialTransaction.INCOME_ONLINE, ""
    return FinancialTransaction.KIND_EXPENSE, "", ""


def _fee_kind(amount: Decimal) -> tuple[str, str, str]:
    if amount > 0:
        return FinancialTransaction.KIND_INCOME, "", ""
    return FinancialTransaction.KIND_EXPENSE, "", FinancialTransaction.EXPENSE_FEES


def _amount(payload: dict, currency: str) -> Decimal:
    code = payload["currency_code"]
    if code != currency:
        raise ValueError(
            f"PayPal transaction currency {code} does not match account currency {currency}"
        )
    return Decimal(payload["value"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _tbilisi_date(value: str) -> date:
    text = value[:-1] + "+0000" if value.endswith("Z") else value
    if "." in text:
        head, tail = text.split(".", 1)
        sign_index = max(tail.rfind("+"), tail.rfind("-"))
        text = head + tail[sign_index:]
    if len(text) > 5 and text[-3] == ":" and text[-6] in "+-":
        text = text[:-3] + text[-2:]
    parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%S%z")
    return parsed.astimezone(_TB).date()


def _counterparty(detail: dict) -> str:
    if "payer_info" not in detail:
        return ""
    payer = detail["payer_info"]
    if "payer_name" in payer:
        name = payer["payer_name"]
        if "alternate_full_name" in name and name["alternate_full_name"] != "":
            return name["alternate_full_name"]
        given = name["given_name"] if "given_name" in name else ""
        surname = name["surname"] if "surname" in name else ""
        full = f"{given} {surname}".strip()
        if full != "":
            return full
    if "email_address" in payer and payer["email_address"] != "":
        return payer["email_address"]
    return ""


def _description(info: dict) -> str:
    if "transaction_subject" in info and info["transaction_subject"] != "":
        return info["transaction_subject"]
    if "transaction_note" in info and info["transaction_note"] != "":
        return info["transaction_note"]
    return info["transaction_event_code"]
