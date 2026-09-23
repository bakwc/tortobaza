import re
import unicodedata

_SOFT_CHARS = frozenset(" \t.-()")
_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff\u2060\u00ad"), None)
_SEPARATOR_MAP = str.maketrans(
    {
        "\u00a0": " ",
        "\u2000": " ",
        "\u2001": " ",
        "\u2002": " ",
        "\u2003": " ",
        "\u2004": " ",
        "\u2005": " ",
        "\u2006": " ",
        "\u2007": " ",
        "\u2008": " ",
        "\u2009": " ",
        "\u200a": " ",
        "\u202f": " ",
        "\u205f": " ",
        "\u3000": " ",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2212": "-",
        "\ufe58": "-",
        "\ufe63": "-",
        "\uff0d": "-",
    }
)
_CC_TOTAL = {
    "995": 12,
    "994": 12,
    "998": 12,
    "996": 12,
    "992": 12,
    "993": 12,
    "380": 12,
    "375": 12,
    "374": 11,
    "373": 11,
    "372": 11,
    "371": 11,
    "370": 11,
    "90": 12,
    "972": 12,
    "971": 12,
    "86": 13,
    "81": 12,
    "49": 13,
    "48": 11,
    "44": 12,
    "43": 12,
    "41": 12,
    "39": 12,
    "34": 11,
    "33": 11,
    "32": 11,
    "31": 11,
    "30": 12,
    "20": 12,
    "7": 11,
    "1": 11,
}
_TG_RESERVED = frozenset(
    {
        "joinchat",
        "share",
        "addstickers",
        "addtheme",
        "proxy",
        "socks",
        "login",
        "boost",
        "invoice",
        "giftcode",
        "telegram",
    }
)
_TG_LINK_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9@])(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/"
    r"([A-Za-z][A-Za-z0-9_]{4,31})(?![A-Za-z0-9_])"
)
_TG_AT_RE = re.compile(
    r"(?<![A-Za-z0-9.])@([A-Za-z][A-Za-z0-9_]{4,31})(?!\.[A-Za-z])"
)
_TG_PREFIX = "tg:"


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_ZERO_WIDTH)
    return text.translate(_SEPARATOR_MAP)


def _is_soft(separator: str) -> bool:
    return separator != "" and all(char in _SOFT_CHARS for char in separator)


def _cc_total(digits: str) -> int | None:
    for size in (3, 2, 1):
        if len(digits) >= size and digits[:size] in _CC_TOTAL:
            return _CC_TOTAL[digits[:size]]
    return None


def _should_close(digits: str) -> bool:
    length = len(digits)
    if length < 7:
        return False
    if length >= 15:
        return True
    total = _cc_total(digits)
    if total is not None:
        return length >= total
    if length == 11 and digits.startswith("8"):
        return True
    if length == 10 and digits.startswith("9"):
        return True
    if length == 9 and not digits.startswith(("7", "8", "0")):
        return True
    return False


def _normalize_raw(digits: str, had_plus: bool) -> str | None:
    if digits.startswith("00"):
        digits = digits[2:]
        had_plus = True
    if len(digits) < 7 or len(digits) > 15:
        return None
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if digits.startswith("7") and len(digits) == 11:
        return digits
    if digits.startswith("995"):
        return digits
    if had_plus:
        if len(digits) <= 9 and _cc_total(digits) is None:
            return "995" + digits
        return digits
    if len(digits) == 10 and digits.startswith("9"):
        return "7" + digits
    if len(digits) <= 9:
        return "995" + digits
    return digits


def _more_digit_group(text: str, index: int) -> bool:
    while index < len(text) and not text[index].isdigit() and text[index] != "+":
        if text[index] not in _SOFT_CHARS:
            return False
        index += 1
    return index < len(text) and text[index].isdigit()


def _mask_span(chars: list[str], start: int, end: int) -> None:
    for index in range(start, end):
        chars[index] = " "


def _telegram_entries(text: str) -> tuple[list[tuple[int, str]], str]:
    matches = [*_TG_LINK_RE.finditer(text), *_TG_AT_RE.finditer(text)]
    matches.sort(key=lambda match: match.start())
    chars = list(text)
    entries: list[tuple[int, str]] = []
    seen: set[str] = set()
    for match in matches:
        if chars[match.start()] == " " and text[match.start()] != " ":
            continue
        username = match.group(1)
        key = username.lower()
        _mask_span(chars, match.start(), match.end())
        if key in _TG_RESERVED or key in seen:
            continue
        seen.add(key)
        entries.append((match.start(), f"{_TG_PREFIX}{username}"))
    return entries, "".join(chars)


def _extract_phone_spans(text: str) -> list[tuple[int, str]]:
    phones: list[tuple[int, str]] = []
    groups: list[str] = []
    had_plus = False
    pending_plus = False
    number_start: int | None = None

    def flush() -> None:
        nonlocal groups, had_plus, number_start
        if groups and number_start is not None:
            normalized = _normalize_raw("".join(groups), had_plus)
            if normalized is not None:
                phones.append((number_start, normalized))
        groups = []
        had_plus = False
        number_start = None

    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == "+":
            if groups:
                flush()
            if number_start is None:
                number_start = index
            pending_plus = True
            index += 1
            continue
        if char.isdigit():
            end = index + 1
            while end < length and text[end].isdigit():
                end += 1
            if pending_plus:
                had_plus = True
                pending_plus = False
            group = text[index:end]
            if groups and len("".join(groups)) + len(group) > 15:
                flush()
            if number_start is None:
                number_start = index
            groups.append(group)
            index = end
            if _more_digit_group(text, index) and _should_close("".join(groups)):
                flush()
            continue
        end = index + 1
        while end < length and not text[end].isdigit() and text[end] != "+":
            end += 1
        if not _is_soft(text[index:end]):
            flush()
            pending_plus = False
        index = end
    flush()
    return phones


def extract_phones(text: str) -> list[str]:
    text = _normalize_text(text)
    _, masked = _telegram_entries(text)
    return [digits for _, digits in _extract_phone_spans(masked)]


def _entries_from_text(text: str) -> list[str]:
    text = _normalize_text(text)
    telegram_entries, masked = _telegram_entries(text)
    merged = sorted([*telegram_entries, *_extract_phone_spans(masked)], key=lambda item: item[0])
    return [value for _, value in merged]


def normalize_phone_digits(contact: str) -> str | None:
    phones = extract_phones(contact)
    if not phones:
        return None
    return phones[0]


def links_for_digits(digits: str) -> dict[str, str]:
    return {
        "e164": f"+{digits}",
        "tel": f"tel:+{digits}",
        "whatsapp": f"https://wa.me/{digits}",
        "telegram": f"https://t.me/+{digits}",
    }


def links_for_stored(value: str) -> dict[str, str | None]:
    if value.startswith(_TG_PREFIX):
        username = value[len(_TG_PREFIX) :]
        return {
            "e164": f"@{username}",
            "tel": None,
            "whatsapp": None,
            "telegram": f"https://t.me/{username}",
        }
    return links_for_digits(value)


def contact_links(contact: str) -> dict[str, str] | None:
    phones = extract_phones(contact)
    if not phones:
        return None
    return links_for_digits(phones[0])


def phones_from_fields(contact: str, nickname: str) -> list[str]:
    phones: list[str] = []
    seen: set[str] = set()
    for source in (contact, nickname):
        for value in _entries_from_text(source):
            key = value.lower() if value.startswith(_TG_PREFIX) else value
            if key in seen:
                continue
            seen.add(key)
            phones.append(value)
    return phones
