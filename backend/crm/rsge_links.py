import re
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone

from crm.internal_transfers import normalize_iban
from crm.models import FinancialTransaction
from rsge.models import Invoice, InvoiceLine, Waybill

WINDOW_DAYS = 4
_CENT = Decimal("0.01")
_IBAN = re.compile(r"GE\d{2}[A-Z0-9]{18}")
_LEGAL = {"შპს", "llc", "shps", "ie", "im", "pos", "wallet"}
_SELLER_NEEDLES = {"445712532": ("kobalaz",)}
_GEORGIAN = {
    "ა": "a",
    "ბ": "b",
    "გ": "g",
    "დ": "d",
    "ე": "e",
    "ვ": "v",
    "ზ": "z",
    "თ": "t",
    "ი": "i",
    "კ": "k",
    "ლ": "l",
    "მ": "m",
    "ნ": "n",
    "ო": "o",
    "პ": "p",
    "ჟ": "zh",
    "რ": "r",
    "ს": "s",
    "ტ": "t",
    "უ": "u",
    "ფ": "f",
    "ქ": "k",
    "ღ": "gh",
    "ყ": "q",
    "შ": "sh",
    "ჩ": "ch",
    "ც": "ts",
    "ძ": "dz",
    "წ": "ts",
    "ჭ": "ch",
    "ხ": "kh",
    "ჯ": "j",
    "ჰ": "h",
}


def sync_rsge_document_links() -> None:
    _link_waybills_to_invoices()
    _link_expenses_to_waybills()
    _link_expenses_to_invoices()
    _propagate_invoices()


def _link_waybills_to_invoices() -> None:
    waybills = list(Waybill.objects.filter(invoices__isnull=True))
    invoices = list(Invoice.objects.filter(waybills__isnull=True))
    waybills, invoices = _link_by_rs_invoice_id(waybills, invoices)
    waybills, invoices = _link_by_line_waybill_id(waybills, invoices)
    _link_waybills_to_invoices_by_tin(waybills, invoices)


def _link_by_rs_invoice_id(
    waybills: list[Waybill],
    invoices: list[Invoice],
) -> tuple[list[Waybill], list[Invoice]]:
    by_rs = {invoice.rs_id: invoice for invoice in invoices}
    pairs: list[tuple[Waybill, Invoice]] = []
    used_waybills: set[int] = set()
    used_invoices: set[int] = set()
    for waybill in waybills:
        if waybill.invoice_id is None:
            continue
        invoice = by_rs.get(waybill.invoice_id)
        if invoice is None:
            continue
        pairs.append((waybill, invoice))
        used_waybills.add(waybill.pk)
        used_invoices.add(invoice.pk)
    _save_waybill_invoices(pairs)
    return _remaining_documents(waybills, invoices, used_waybills, used_invoices)


def _link_by_line_waybill_id(
    waybills: list[Waybill],
    invoices: list[Invoice],
) -> tuple[list[Waybill], list[Invoice]]:
    invoices_by_pk = {invoice.pk: invoice for invoice in invoices}
    waybills_by_rs = {waybill.rs_id: waybill for waybill in waybills}
    pairs: list[tuple[Waybill, Invoice]] = []
    seen: set[tuple[int, int]] = set()
    used_waybills: set[int] = set()
    used_invoices: set[int] = set()
    lines = InvoiceLine.objects.filter(
        waybill_id__isnull=False,
        invoice_id__in=invoices_by_pk,
    )
    for line in lines:
        waybill = waybills_by_rs.get(line.waybill_id)
        invoice = invoices_by_pk.get(line.invoice_id)
        if waybill is None or invoice is None:
            continue
        key = (waybill.pk, invoice.pk)
        if key in seen:
            continue
        seen.add(key)
        pairs.append((waybill, invoice))
        used_waybills.add(waybill.pk)
        used_invoices.add(invoice.pk)
    _save_waybill_invoices(pairs)
    return _remaining_documents(waybills, invoices, used_waybills, used_invoices)


def _link_waybills_to_invoices_by_tin(waybills: list[Waybill], invoices: list[Invoice]) -> None:
    preferences: list[tuple[int, Waybill, Invoice]] = []
    for waybill in waybills:
        day = _local_day(waybill.create_date)
        candidates: list[tuple[int, Invoice]] = []
        for invoice in invoices:
            if waybill.seller_tin != invoice.seller_tin:
                continue
            if not _same_document_amount(waybill.full_amount, invoice.amount):
                continue
            distance = _invoice_distance(invoice, day)
            if distance <= WINDOW_DAYS:
                candidates.append((distance, invoice))
        if not candidates:
            continue
        best = min(distance for distance, _invoice in candidates)
        closest = [invoice for distance, invoice in candidates if distance == best]
        if len(closest) != 1:
            continue
        preferences.append((best, waybill, closest[0]))
    grouped: dict[int, list[tuple[int, Waybill, Invoice]]] = {}
    for distance, waybill, invoice in preferences:
        grouped.setdefault(invoice.pk, []).append((distance, waybill, invoice))
    pairs: list[tuple[Waybill, Invoice]] = []
    for group in grouped.values():
        group.sort(key=lambda item: (item[0], _local_day(item[1].create_date), item[1].pk))
        if len(group) > 1 and group[0][0] == group[1][0]:
            continue
        _distance, waybill, invoice = group[0]
        pairs.append((waybill, invoice))
    _save_waybill_invoices(pairs)


def _link_expenses_to_waybills() -> None:
    transactions = _unlinked_expenses("waybills")
    waybills = list(Waybill.objects.filter(financial_transactions__isnull=True))
    by_iban, waybills, transactions = _assign(
        waybills,
        transactions,
        _waybill_iban_match,
        _waybill_distance,
    )
    by_name, waybills, transactions = _assign(
        waybills,
        transactions,
        _waybill_name_match,
        _waybill_distance,
    )
    splits, _waybills, _transactions = _split(
        waybills,
        transactions,
        _waybill_amount,
        _waybill_ibans,
        _waybill_distance_from_day,
    )
    pairs = by_iban + by_name
    for group, waybill in splits:
        for transaction in group:
            pairs.append((transaction, waybill))
    _save_transaction_waybills(pairs)


def _link_expenses_to_invoices() -> None:
    transactions = _unlinked_expenses("invoices")
    invoices = list(Invoice.objects.filter(financial_transactions__isnull=True))
    by_iban, invoices, transactions = _assign(
        invoices,
        transactions,
        _invoice_iban_match,
        _invoice_transaction_distance,
    )
    by_name, invoices, transactions = _assign(
        invoices,
        transactions,
        _invoice_name_match,
        _invoice_transaction_distance,
    )
    splits, _invoices, _transactions = _split(
        invoices,
        transactions,
        _invoice_amount,
        _invoice_ibans,
        _invoice_distance,
    )
    pairs = by_iban + by_name
    for group, invoice in splits:
        for transaction in group:
            pairs.append((transaction, invoice))
    _save_transaction_invoices(pairs)


def _propagate_invoices() -> None:
    through = FinancialTransaction.invoices.through
    existing = set(through.objects.values_list("financialtransaction_id", "invoice_id"))
    links = []
    transactions = (
        FinancialTransaction.objects.filter(waybills__invoices__isnull=False)
        .distinct()
        .prefetch_related("waybills__invoices")
    )
    for transaction in transactions:
        for waybill in transaction.waybills.all():
            for invoice in waybill.invoices.all():
                key = (transaction.pk, invoice.pk)
                if key in existing:
                    continue
                existing.add(key)
                links.append(
                    through(
                        financialtransaction_id=transaction.pk,
                        invoice_id=invoice.pk,
                    )
                )
    if links:
        through.objects.bulk_create(links)


def _unlinked_expenses(field: str) -> list[FinancialTransaction]:
    return list(
        FinancialTransaction.objects.filter(
            kind=FinancialTransaction.KIND_EXPENSE,
            **{f"{field}__isnull": True},
        ).order_by("date", "pk")
    )


def _assign(
    documents: list,
    transactions: list[FinancialTransaction],
    matched: Callable,
    distance_of: Callable,
) -> tuple[list[tuple[FinancialTransaction, object]], list, list[FinancialTransaction]]:
    preferences: list[tuple[int, FinancialTransaction, object]] = []
    for transaction in transactions:
        candidates: list[tuple[int, object]] = []
        for document in documents:
            if not matched(document, transaction):
                continue
            distance = distance_of(document, transaction)
            if distance <= WINDOW_DAYS:
                candidates.append((distance, document))
        if not candidates:
            continue
        best = min(distance for distance, _document in candidates)
        closest = [document for distance, document in candidates if distance == best]
        if len(closest) != 1:
            continue
        preferences.append((best, transaction, closest[0]))
    grouped: dict[int, list[tuple[int, FinancialTransaction, object]]] = {}
    for distance, transaction, document in preferences:
        grouped.setdefault(document.pk, []).append((distance, transaction, document))
    linked: list[tuple[FinancialTransaction, object]] = []
    used_transactions: set[int] = set()
    used_documents: set[int] = set()
    for group in grouped.values():
        group.sort(key=lambda item: (item[0], item[1].date, item[1].pk))
        if len(group) > 1 and group[0][0] == group[1][0]:
            continue
        _distance, transaction, document = group[0]
        linked.append((transaction, document))
        used_transactions.add(transaction.pk)
        used_documents.add(document.pk)
    remaining_documents = [document for document in documents if document.pk not in used_documents]
    remaining_transactions = [
        transaction for transaction in transactions if transaction.pk not in used_transactions
    ]
    return linked, remaining_documents, remaining_transactions


def _split(
    documents: list,
    transactions: list[FinancialTransaction],
    amount_of: Callable,
    ibans_of: Callable,
    distance_of: Callable[[object, date], int],
) -> tuple[list[tuple[list[FinancialTransaction], object]], list, list[FinancialTransaction]]:
    groups: dict[tuple[str, date], list[FinancialTransaction]] = {}
    for transaction in transactions:
        iban = normalize_iban(transaction.counterparty_iban)
        if iban == "":
            continue
        groups.setdefault((iban, transaction.date), []).append(transaction)
    proposals: list[tuple[list[FinancialTransaction], object]] = []
    for (iban, day), group in groups.items():
        if len(group) < 2:
            continue
        total = _money(sum((abs(transaction.amount) for transaction in group), Decimal("0")))
        amount_matches = [
            document
            for document in documents
            if _money(amount_of(document)) == total and distance_of(document, day) <= WINDOW_DAYS
        ]
        if len(amount_matches) != 1:
            continue
        document = amount_matches[0]
        if iban not in ibans_of(document):
            continue
        proposals.append((group, document))
    by_document: dict[int, list[tuple[list[FinancialTransaction], object]]] = {}
    for proposal in proposals:
        by_document.setdefault(proposal[1].pk, []).append(proposal)
    linked: list[tuple[list[FinancialTransaction], object]] = []
    used_transactions: set[int] = set()
    used_documents: set[int] = set()
    for items in by_document.values():
        if len(items) != 1:
            continue
        group, document = items[0]
        linked.append((group, document))
        used_documents.add(document.pk)
        for transaction in group:
            used_transactions.add(transaction.pk)
    remaining_documents = [document for document in documents if document.pk not in used_documents]
    remaining_transactions = [
        transaction for transaction in transactions if transaction.pk not in used_transactions
    ]
    return linked, remaining_documents, remaining_transactions


def _waybill_iban_match(waybill: Waybill, transaction: FinancialTransaction) -> bool:
    iban = normalize_iban(transaction.counterparty_iban)
    if iban == "":
        return False
    if iban not in _waybill_ibans(waybill):
        return False
    return _same_tx_amount(waybill.full_amount, transaction.amount)


def _waybill_name_match(waybill: Waybill, transaction: FinancialTransaction) -> bool:
    if not _names_match(waybill.seller_name, waybill.seller_tin, transaction.counterparty_name):
        return False
    return _same_tx_amount(waybill.full_amount, transaction.amount)


def _invoice_iban_match(invoice: Invoice, transaction: FinancialTransaction) -> bool:
    iban = normalize_iban(transaction.counterparty_iban)
    if iban == "":
        return False
    if iban not in _invoice_ibans(invoice):
        return False
    return _same_tx_amount(invoice.amount, transaction.amount)


def _invoice_name_match(invoice: Invoice, transaction: FinancialTransaction) -> bool:
    if not _names_match(invoice.org_name, invoice.seller_tin, transaction.counterparty_name):
        return False
    return _same_tx_amount(invoice.amount, transaction.amount)


def _waybill_distance(waybill: Waybill, transaction: FinancialTransaction) -> int:
    return _waybill_distance_from_day(waybill, transaction.date)


def _waybill_distance_from_day(waybill: Waybill, day: date) -> int:
    return abs((_local_day(waybill.create_date) - day).days)


def _invoice_transaction_distance(invoice: Invoice, transaction: FinancialTransaction) -> int:
    return _invoice_distance(invoice, transaction.date)


def _invoice_distance(invoice: Invoice, day: date) -> int:
    return min(
        abs((_local_day(invoice.operation_dt) - day).days),
        abs((_local_day(invoice.reg_dt) - day).days),
    )


def _waybill_amount(waybill: Waybill) -> Decimal:
    return waybill.full_amount


def _invoice_amount(invoice: Invoice) -> Decimal:
    return invoice.amount


def _waybill_ibans(waybill: Waybill) -> set[str]:
    return _ibans(waybill.waybill_comment)


def _invoice_ibans(invoice: Invoice) -> set[str]:
    return _ibans(f"{invoice.notes}\n{invoice.note}")


def _ibans(text: str) -> set[str]:
    return {normalize_iban(match) for match in _IBAN.findall(text.upper())}


def _names_match(seller_name: str, seller_tin: str, counterparty_name: str) -> bool:
    blob = _letters(counterparty_name).casefold()
    folded = counterparty_name.casefold()
    for needle in _SELLER_NEEDLES.get(seller_tin, ()):
        if needle in blob:
            return True
    other_tokens = _counterparty_tokens(counterparty_name)
    for token in _seller_tokens(seller_name):
        if len(token) < 4:
            continue
        if token in folded:
            return True
        latin = _transliterate(token)
        if len(latin) >= 4 and latin in blob:
            return True
        for other in other_tokens:
            if len(latin) > 5 and len(other) > 5 and latin[:5] == other[:5]:
                return True
    return False


def _seller_tokens(name: str) -> list[str]:
    tokens = []
    for raw in name.split():
        token = _letters(raw).casefold()
        if token == "" or token in _LEGAL:
            continue
        tokens.append(token)
    return tokens


def _counterparty_tokens(name: str) -> list[str]:
    tokens = []
    for raw in name.casefold().replace("-", " ").replace(",", " ").split():
        token = _letters(raw)
        if token == "" or token in _LEGAL:
            continue
        tokens.append(token)
    return tokens


def _transliterate(token: str) -> str:
    return "".join(_GEORGIAN.get(char, char) for char in token.casefold())


def _letters(value: str) -> str:
    return "".join(char for char in value if char.isalpha())


def _same_tx_amount(document_amount: Decimal, tx_amount: Decimal) -> bool:
    return _money(document_amount) == _money(abs(tx_amount))


def _same_document_amount(left: Decimal, right: Decimal) -> bool:
    return _money(left) == _money(right)


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT)


def _local_day(value: datetime) -> date:
    return timezone.localtime(value).date()


def _remaining_documents(
    waybills: list[Waybill],
    invoices: list[Invoice],
    used_waybills: set[int],
    used_invoices: set[int],
) -> tuple[list[Waybill], list[Invoice]]:
    return (
        [waybill for waybill in waybills if waybill.pk not in used_waybills],
        [invoice for invoice in invoices if invoice.pk not in used_invoices],
    )


def _save_waybill_invoices(pairs: list[tuple[Waybill, Invoice]]) -> None:
    if not pairs:
        return
    Waybill.invoices.through.objects.bulk_create(
        [
            Waybill.invoices.through(waybill_id=waybill.pk, invoice_id=invoice.pk)
            for waybill, invoice in pairs
        ]
    )


def _save_transaction_waybills(pairs: list[tuple[FinancialTransaction, Waybill]]) -> None:
    if not pairs:
        return
    FinancialTransaction.waybills.through.objects.bulk_create(
        [
            FinancialTransaction.waybills.through(
                financialtransaction_id=transaction.pk,
                waybill_id=waybill.pk,
            )
            for transaction, waybill in pairs
        ]
    )


def _save_transaction_invoices(pairs: list[tuple[FinancialTransaction, Invoice]]) -> None:
    if not pairs:
        return
    FinancialTransaction.invoices.through.objects.bulk_create(
        [
            FinancialTransaction.invoices.through(
                financialtransaction_id=transaction.pk,
                invoice_id=invoice.pk,
            )
            for transaction, invoice in pairs
        ]
    )
