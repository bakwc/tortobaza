import calendar
import imaplib
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from email import message_from_bytes
from email.header import decode_header
from email.message import Message
from email.utils import parsedate, parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from crm.models import CardSmsMessage, FinancialAccount, FinancialTransaction
from crm.transaction_rules import assign_expense_types
from tortobaza.finance_db import use_finance_db

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
SUBJECT = "Test"
WINDOW = timedelta(hours=12)
_FINANCE_DBS = ("default", "personal")
_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}
BOG_BUSINESS_GEL = "BOG business GEL"
_PURCHASE_RE = re.compile(r"Purchase:\s*([A-Z]{3})(\d+\.\d{2})")
_CARD_RE = re.compile(r"Card:\*+(\d{4})")
_DATE_RE = re.compile(r"(\d{2})[./](\d{2})[./](\d{4})")
_OPERATION_RE = re.compile(r"gasavali|charicxva", re.IGNORECASE)
_ACCOUNT_AMOUNT_RE = re.compile(r"([A-Z]{3})([\d,]+\.\d{2})")
_DECIMAL_AMOUNT_RE = re.compile(r"\d+\.\d{2}")
_NASHTI_RE = re.compile(r"nashti:\s*[A-Z]{3}[\d,]+\.\d{2}", re.IGNORECASE)
_VISGAN_RE = re.compile(r"visgan:\s*(.+)", re.IGNORECASE)
_INTERNALDATE_RE = re.compile(rb'INTERNALDATE "([^"]+)"')


@dataclass(frozen=True)
class ParsedCardSms:
    card_last4: str
    currency: str
    amount: Decimal
    merchant: str
    sms_date: date
    kind: str


@dataclass(frozen=True)
class InboxMessage:
    message_id: str
    received_at: datetime
    body: str


class _HtmlText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.parts.append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _HtmlText()
    parser.feed(unescape(html))
    parser.close()
    return "".join(parser.parts)


def parse_card_sms(body: str) -> ParsedCardSms | None:
    lines = [line.strip() for line in body.splitlines() if line.strip() != ""]
    if len(lines) < 3:
        return None
    purchase = _parse_purchase(lines)
    if purchase is not None:
        return purchase
    return _parse_account_operation(lines)


def import_card_sms() -> None:
    now = timezone.now()
    for item in fetch_recent_test_messages(now):
        _store_message(item)
    _parse_unparsed()
    _match_pending()


def fetch_recent_test_messages(now: datetime) -> list[InboxMessage]:
    since = now - WINDOW
    client = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    client.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    client.select("INBOX")
    typ, data = client.search(None, "SINCE", _imap_date(since), "SUBJECT", SUBJECT)
    if typ != "OK":
        raise RuntimeError(typ)
    numbers = [] if not data[0] else data[0].split()
    messages: list[InboxMessage] = []
    for number in numbers:
        item = _read_message(client, number, since)
        if item is not None:
            messages.append(item)
    client.logout()
    return messages


def _store_message(item: InboxMessage) -> None:
    row, created = CardSmsMessage.objects.get_or_create(
        message_id=item.message_id,
        defaults={
            "received_at": item.received_at,
            "raw_body": item.body,
            "status": CardSmsMessage.STATUS_UNPARSED,
        },
    )
    if not created:
        return
    _apply_parsed(row, item.body)


def _match_pending() -> None:
    pending = list(
        CardSmsMessage.objects.filter(
            status__in=[CardSmsMessage.STATUS_UNMATCHED, CardSmsMessage.STATUS_AMBIGUOUS],
        )
    )
    for row in pending:
        _match_row(row)


def _match_row(row: CardSmsMessage) -> None:
    if row.card_last4 == "":
        found = _matching_named_accounts(BOG_BUSINESS_GEL, row.currency)
    else:
        found = _matching_accounts(row.card_last4, row.currency)
    if len(found) == 0:
        row.status = CardSmsMessage.STATUS_UNMATCHED
        row.finance_db = ""
        row.transaction_id = None
        row.save()
        return
    if len(found) > 1:
        row.status = CardSmsMessage.STATUS_AMBIGUOUS
        row.finance_db = ""
        row.transaction_id = None
        row.save()
        return
    alias, account_id = found[0]
    row.transaction_id = _insert_transaction(alias, account_id, row)
    row.finance_db = alias
    row.status = CardSmsMessage.STATUS_INSERTED
    row.save()


def _matching_accounts(card_last4: str, currency: str) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for alias in _FINANCE_DBS:
        with use_finance_db(alias):
            for account in FinancialAccount.objects.all():
                if card_last4 in _cards_of(account) and account.currency == currency:
                    found.append((alias, account.pk))
    return found


def _cards_of(account: FinancialAccount) -> set[str]:
    return {part.strip() for part in account.cards.split(",") if part.strip() != ""}


def _insert_transaction(alias: str, account_id: int, row: CardSmsMessage) -> int:
    with use_finance_db(alias):
        with transaction.atomic(using=alias):
            if row.transaction_id is not None:
                linked = FinancialTransaction.objects.filter(
                    pk=row.transaction_id,
                    account_id=account_id,
                ).first()
                if linked is not None:
                    return linked.pk
            existing = FinancialTransaction.objects.filter(
                account_id=account_id,
                external_id=row.message_id,
            ).first()
            if existing is not None:
                return existing.pk
            account = FinancialAccount.objects.get(pk=account_id)
            if row.kind == CardSmsMessage.KIND_INCOME:
                amount = row.amount
                kind = FinancialTransaction.KIND_INCOME
                income_type = FinancialTransaction.INCOME_TRANSFER
            else:
                amount = -row.amount
                kind = FinancialTransaction.KIND_EXPENSE
                income_type = ""
            created = FinancialTransaction(
                account=account,
                date=row.sms_date,
                amount=amount,
                kind=kind,
                income_type=income_type,
                counterparty_name=row.merchant,
                description=row.merchant,
                external_id=row.message_id,
            )
            if kind == FinancialTransaction.KIND_EXPENSE:
                assign_expense_types([created])
            created.save()
            return created.pk


def _read_message(client, number: bytes, since: datetime) -> InboxMessage | None:
    typ, data = client.fetch(number, "(INTERNALDATE BODY.PEEK[])")
    if typ != "OK":
        raise RuntimeError(typ)
    internal, raw = _fetched_message(data)
    message = message_from_bytes(raw)
    if _header_text(message, "Subject") != SUBJECT:
        return None
    message_id = _header_text(message, "Message-ID")
    if message_id == "":
        return None
    received_at = _received_at(message, internal)
    if received_at < since:
        return None
    return InboxMessage(message_id=message_id, received_at=received_at, body=_message_body(message))


def _fetched_message(data) -> tuple[datetime, bytes]:
    meta = data[0][0]
    raw = data[0][1]
    if not isinstance(meta, bytes) or not isinstance(raw, bytes):
        raise RuntimeError("Unexpected IMAP fetch response")
    match = _INTERNALDATE_RE.search(meta)
    if match is None:
        raise RuntimeError("IMAP response has no INTERNALDATE")
    return _parse_internaldate(match.group(1).decode()), raw


def _received_at(message: Message, internal: datetime) -> datetime:
    raw = message.get("Date")
    if raw is None or parsedate(raw) is None:
        return internal
    received = parsedate_to_datetime(raw)
    if received.tzinfo is None:
        return timezone.make_aware(received, timezone.utc)
    return received


def _message_body(message: Message) -> str:
    if message.is_multipart():
        html_body = ""
        plain_body = ""
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_disposition() == "attachment":
                continue
            text = _part_text(part)
            if text is None:
                continue
            content_type = part.get_content_type()
            if content_type == "text/html" and html_body == "":
                html_body = text
            elif content_type == "text/plain" and plain_body == "":
                plain_body = text
        if html_body != "":
            return html_to_text(html_body)
        return plain_body
    text = _part_text(message)
    if text is None:
        return ""
    if message.get_content_type() == "text/html":
        return html_to_text(text)
    return text


def _part_text(part: Message) -> str | None:
    payload = part.get_payload(decode=True)
    if payload is None:
        return None
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset)


def _header_text(message: Message, name: str) -> str:
    value = message.get(name)
    if value is None:
        return ""
    chunks: list[str] = []
    for part, charset in decode_header(value):
        if isinstance(part, bytes):
            chunks.append(part.decode(charset or "utf-8"))
        else:
            chunks.append(part)
    return "".join(chunks).strip()


def _parse_purchase(lines: list[str]) -> ParsedCardSms | None:
    purchase = _PURCHASE_RE.fullmatch(lines[0])
    sms_date = _sms_date(lines[-1])
    if purchase is None or sms_date is None:
        return None
    card_index = _card_index(lines)
    if card_index is None or card_index == 0 or card_index == len(lines) - 1:
        return None
    card_match = _CARD_RE.fullmatch(lines[card_index])
    merchant_lines = _merchant_lines(lines[card_index + 1 : -1])
    if card_match is None or len(merchant_lines) == 0:
        return None
    amount = Decimal(purchase.group(2)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return ParsedCardSms(
        card_last4=card_match.group(1),
        currency=purchase.group(1),
        amount=amount,
        merchant=" ".join(merchant_lines),
        sms_date=sms_date,
        kind=CardSmsMessage.KIND_EXPENSE,
    )


def _parse_account_operation(lines: list[str]) -> ParsedCardSms | None:
    operation = _OPERATION_RE.fullmatch(lines[0])
    sms_date = _sms_date(lines[-1])
    if operation is None or sms_date is None:
        return None
    amount_index = _single_index(lines, _account_amount_line)
    balance_index = _single_index(lines, _NASHTI_RE.fullmatch)
    if amount_index is None or balance_index is None:
        return None
    if amount_index < 2 or balance_index <= amount_index or balance_index >= len(lines) - 1:
        return None
    parsed_amount = _account_amount(lines[amount_index])
    merchant = _account_merchant(lines[amount_index + 1 : balance_index])
    if parsed_amount is None or merchant is None:
        return None
    currency, amount = parsed_amount
    if operation.group(0).lower() == "charicxva":
        kind = CardSmsMessage.KIND_INCOME
    else:
        kind = CardSmsMessage.KIND_EXPENSE
    return ParsedCardSms(
        card_last4="",
        currency=currency,
        amount=amount,
        merchant=merchant,
        sms_date=sms_date,
        kind=kind,
    )


def _parse_unparsed() -> None:
    pending = list(CardSmsMessage.objects.filter(status=CardSmsMessage.STATUS_UNPARSED))
    for row in pending:
        _apply_parsed(row, row.raw_body)


def _apply_parsed(row: CardSmsMessage, body: str) -> None:
    parsed = parse_card_sms(body)
    if parsed is None:
        return
    row.card_last4 = parsed.card_last4
    row.currency = parsed.currency
    row.amount = parsed.amount
    row.merchant = parsed.merchant
    row.sms_date = parsed.sms_date
    row.kind = parsed.kind
    row.status = CardSmsMessage.STATUS_UNMATCHED
    row.save()


def _matching_named_accounts(name: str, currency: str) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for alias in _FINANCE_DBS:
        with use_finance_db(alias):
            for account in FinancialAccount.objects.filter(name=name, currency=currency):
                found.append((alias, account.pk))
    return found


def _account_amount_line(line: str) -> bool:
    return _account_amount(line) is not None


def _account_amount(line: str) -> tuple[str, Decimal] | None:
    match = _ACCOUNT_AMOUNT_RE.fullmatch(line)
    if match is None:
        return None
    raw = match.group(2).replace(",", "")
    if _DECIMAL_AMOUNT_RE.fullmatch(raw) is None:
        return None
    amount = Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return match.group(1), amount


def _account_merchant(lines: list[str]) -> str | None:
    visgan: list[str] = []
    details: list[str] = []
    for line in lines:
        match = _VISGAN_RE.fullmatch(line)
        if match is None:
            details.append(line)
            continue
        name = match.group(1).strip()
        if name == "":
            return None
        visgan.append(name)
    if len(visgan) == 1:
        return visgan[0]
    if len(visgan) == 0 and len(details) > 0:
        return " ".join(details)
    return None


def _single_index(lines: list[str], matches: Callable[[str], object]) -> int | None:
    found = [index for index, line in enumerate(lines) if matches(line)]
    if len(found) != 1:
        return None
    return found[0]


def _sms_date(line: str) -> date | None:
    match = _DATE_RE.fullmatch(line)
    if match is None:
        return None
    day = int(match.group(1))
    month = int(match.group(2))
    year = int(match.group(3))
    if month < 1 or month > 12:
        return None
    if day < 1 or day > calendar.monthrange(year, month)[1]:
        return None
    return date(year, month, day)


def _card_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        if _CARD_RE.fullmatch(line) is not None:
            return index
    return None


def _merchant_lines(lines: list[str]) -> list[str]:
    merchant: list[str] = []
    for line in lines:
        lowered = line.lower()
        if lowered.startswith("you received:") or lowered.startswith("total:"):
            continue
        merchant.append(line)
    return merchant


def _parse_internaldate(value: str) -> datetime:
    day_text, month_text, rest = value.split("-", 2)
    year_text, time_text, tz_text = rest.split(" ")
    hour_text, minute_text, second_text = time_text.split(":")
    tzinfo = datetime.strptime(tz_text, "%z").tzinfo
    return datetime(
        int(year_text),
        _MONTHS[month_text],
        int(day_text),
        int(hour_text),
        int(minute_text),
        int(second_text),
        tzinfo=tzinfo,
    )


def _imap_date(value: datetime) -> str:
    month = next(name for name, number in _MONTHS.items() if number == value.month)
    return f"{value.day:02d}-{month}-{value.year}"
