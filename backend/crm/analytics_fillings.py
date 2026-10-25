import re

_CANONICAL: dict[str, str] = {}


def normalize_text(text: str) -> str:
    lowered = text.casefold().replace("ё", "е")
    return re.sub(r"\s+", " ", lowered).strip()


def display_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _add(canonical: str, aliases: tuple[str, ...]) -> None:
    for alias in (canonical, *aliases):
        key = normalize_text(alias)
        previous = _CANONICAL.get(key)
        if previous is not None and previous != canonical:
            raise ValueError(key)
        _CANONICAL[key] = canonical


_add("Фисташка малина", ("Фисташка и малина", "pistachio raspberry", "pistachio and raspberry"))
_add("Шоколад вишня", ("chocolate cherry", "chocolate and cherries", "\u0421hocolate and cherry"))
_add("Сникерс", ("snickers",))
_add("Манго маракуйя", ("Манго и маракуйя", "mango passion fruit", "mango and passion fruit"))
_add("Криспи карамель", ())
_add(
    "Криспи банан карамель",
    ("Криспи банан и карамель", "Caramel, banana and crispy", "Криспи карамель банан"),
)
_add("Ваниль клубника", ("vanilla with strawberries",))
_add("Морковный с грушей", ("морковь и груша", "carrot with pear filling"))
_add("Морковный", ())
_add("Кб вишня", ())
_add("Кб клубника", ())
_add("Молочная девочка", ())
_add("Молочная девочка с малиной", ("Молочная девочка С МАЛИНОЙ",))
_add("Молочная девочка с клубникой", ("Milky girl with strawberry",))
_add("Молочная девочка без клубники и каких либо ягод !!!!! Тупо коржи и крем", ())
_add("Медовик", ())
_add("Тирамису", ())
_add("Красный бархат клубника", ("red velvet with strawberries", "Красный бархат с клубникой"))
_add("Шоколад клубника", ())
_add("Шоколадный бисквит и шоколадный крем", ())
_add("Шоколадный бисквит и соленая карамель", ())
_add("Шоколад вишня с шоколадным кремом", ())
_add("Шоколад вишня и добавить грецких Орехов", ())
_add("Пьяная вишня", ())
_add("Любая вкусная", ())
_add("Любая", ())
_add("Кристи карамель", ())
_add("Криспи карамель с шоколадным кремом", ())
_add("Криспи карамель без яиц", ("Криспи карамель БЕЗ ЯИЦ",))
_add("Криспи банан", ())
_add("Зимняя вишня", ())
_add("Ореховое наслаждение", ("ореховое наслаждение",))
_add("Ванильный бисквит с лимонным курдом", ("ванильный бисквит с лимонным курдом",))
_add("Ванильный бисквит и смородиновое конфи", ())
_add("Ванильная основа и малиновое конфи", ())
_add("Ваниль малиновое конфи", ())
_add("Ваниль и малиновое конфи", ())
_add("Strawberry", ())
_add("Сникерс БЕЗ ЯИЦ И ОРЕХОВ И СОЛИ В КАРАМЕЛИ , но добавить шарики криспи", ())


def canonical_filling(text: str) -> str | None:
    return _CANONICAL.get(normalize_text(text))


def stored_filling(text: str) -> str:
    canonical = canonical_filling(text)
    if canonical is not None:
        return canonical
    return display_text(text)


def canonical_names() -> list[str]:
    return sorted(set(_CANONICAL.values()))
