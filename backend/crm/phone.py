import re

_PHONE_RE = re.compile(r"\+?\d[\d \t\-().]{5,}\d")


def normalize_phone_digits(contact: str) -> str | None:
    match = _PHONE_RE.search(contact)
    if not match:
        return None
    raw = match.group(0)
    had_plus = raw.lstrip().startswith("+")
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 7:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if digits.startswith("7") and len(digits) == 11:
        return digits
    if digits.startswith("995"):
        return digits
    if had_plus:
        return digits
    return "995" + digits


def contact_links(contact: str) -> dict[str, str] | None:
    digits = normalize_phone_digits(contact)
    if digits is None:
        return None
    return {
        "e164": f"+{digits}",
        "tel": f"tel:+{digits}",
        "whatsapp": f"https://wa.me/{digits}",
        "telegram": f"https://t.me/+{digits}",
    }
