import json
import re
import shutil
import unicodedata
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from struct import unpack
from xml.etree import ElementTree

import Quartz
from numbers_parser.cell import _unpack_decimal128
from numbers_parser.generated import TSTArchives_pb2 as TST
from numbers_parser.iwafile import IWAFile
from numbers_parser.model import get_storage_buffers_for_row

SOURCE = Path("/Users/fippo/Documents/tech-cards")
ROOT = Path(__file__).resolve().parents[1] / "backend" / "menu" / "data"
IMAGES = ROOT / "images"
EGG_GRAMS = Decimal("50")
YOLK_GRAMS = Decimal("18")
PIECE_NOTE = "1 шт = 50 г"
YOLK_NOTE = "1 шт = 18 г"

EXACT_NAMES = {
    "мука": "Мука пшеничная",
    "мука пшеничная": "Мука пшеничная",
    "миндальная мука": "Миндальная мука",
    "яйцо": "Яйцо",
    "яйца": "Яйцо",
    "яйцо куриное": "Яйцо",
    "белок": "Яичный белок",
    "белки": "Яичный белок",
    "белки яичные": "Яичный белок",
    "желток": "Желток",
    "желтки": "Желток",
    "сахар": "Сахар",
    "сахарный песок": "Сахар",
    "сахар тростниковый": "Сахар тростниковый",
    "сахар тросниковый": "Сахар тростниковый",
    "сахарная пудра": "Сахарная пудра",
    "масло": "Масло сливочное",
    "масло сливочное": "Масло сливочное",
    "сливочное масло": "Масло сливочное",
    "масло слив.": "Масло сливочное",
    "растительное масло": "Масло растительное",
    "масло растительное": "Масло растительное",
    "масло подсолнечное": "Масло подсолнечное",
    "сливки": "Сливки 33%",
    "сливки 33": "Сливки 33%",
    "сливки 33%": "Сливки 33%",
    "сливки петмол 33%": "Сливки 33%",
    "сливки петмол 33 %": "Сливки 33%",
    "сливки петмол": "Сливки 33%",
    "сливки 1 часть": "Сливки 33%",
    "сливки 2 часть": "Сливки 33%",
    "сливки взбитые": "Сливки 33%",
    "кремчиз": "Кремчиз",
    "крем чиз": "Кремчиз",
    "маскарпоне или кремчиз": "Кремчиз",
    "сыр «маскарпоне»": "Маскарпоне",
    "сыр маскарпоне": "Маскарпоне",
    "маскарпоне": "Маскарпоне",
    "сыр творожный": "Сыр творожный",
    "какао": "Какао",
    "какао-порошок": "Какао",
    "пшеничная мука": "Мука пшеничная",
    "тростниковый сахар": "Сахар тростниковый",
    "фисташки очищенные": "Фисташка",
    "молоко горячее": "Молоко",
    "вода ледяная": "Вода",
    "какао алко": "Какао алкализованное",
    "какао алколизированный": "Какао алкализованное",
    "какао-масло": "Какао-масло",
    "какао масло": "Какао-масло",
    "сгущенка": "Сгущённое молоко",
    "мед": "Мёд",
    "мёд": "Мёд",
    "сода": "Сода",
    "сода пищевая": "Сода",
    "разрыхлитель": "Разрыхлитель",
    "ванилин": "Ванилин",
    "ванильная паста": "Ванильная паста",
    "ванильный сахар": "Ванильный сахар",
    "ванильный экстракт": "Ванильный экстракт",
    "соль": "Соль",
    "вода": "Вода",
    "вода на желатин": "Вода",
    "вода для крахмала": "Вода",
    "вода для желатина": "Вода",
    "желатин": "Желатин",
    "глюкозный сироп": "Глюкозный сироп",
    "молоко": "Молоко",
    "уксус": "Уксус 6%",
    "уксус 6%": "Уксус 6%",
    "крахмал": "Кукурузный крахмал",
    "крахмал кукурузный": "Кукурузный крахмал",
    "кукурузный крахмал": "Кукурузный крахмал",
    "пектин nh": "Пектин NH",
    "пектин": "Пектин",
    "лимонная кислота": "Лимонная кислота",
    "пюре маракуйя": "Пюре маракуйи",
    "пюре маракуйи": "Пюре маракуйи",
    "пюре манго": "Пюре манго",
    "пюре малины": "Пюре малины",
    "малиновое пюре": "Пюре малины",
    "малина": "Малина",
    "агар-агар": "Агар-агар",
    "корки лайма": "Корки лайма",
    "сок лайма": "Сок лайма",
    "хвостики от мандаринов": "Хвостик мандарина",
    "хвостик мандарина": "Хвостик мандарина",
    "пюре лайма": "Пюре лайма",
    "облепиховое пюре": "Пюре облепихи",
    "пюре кокос": "Пюре кокоса",
    "кокос": "Кокосовая стружка",
    "кокосовая стружка": "Кокосовая стружка",
    "клубника": "Клубника",
    "клубника б/з": "Клубника",
    "кусочки манго замороз": "Манго",
    "банан": "Банан",
    "фисташковая паста": "Фисташковая паста",
    "паста фисташка": "Фисташковая паста",
    "фундучная паста": "Фундучная паста",
    "фундучное пралине": "Фундучное пралине",
    "белый шоколад": "Белый шоколад",
    "шоколад белый": "Белый шоколад",
    "молочный шоколад": "Молочный шоколад",
    "шоколад молочный": "Молочный шоколад",
    "темный шоколад": "Тёмный шоколад",
    "шоколад": "Шоколад",
    "корица": "Корица",
    "корица молотая": "Корица",
    "морковь": "Морковь",
    "грецкий орех": "Грецкий орех",
    "орех пекан": "Пекан",
    "изюм золотой": "Изюм",
    "изюм": "Изюм",
    "мацони": "Мацони",
    "сметана 30%": "Сметана 30%",
    "сметана 25-30%": "Сметана 30%",
    "криспи крошка": "Криспи",
    "катаифи": "Катаифи",
    "песочное печенье": "Песочное печенье",
    "маргарин": "Маргарин",
    "мускатный орех": "Мускатный орех",
    "ксантановая камедь": "Ксантановая камедь",
    "ароматизатор": "Ароматизатор",
    "краситель": "Краситель",
    "сок лимона": "Сок лимона",
    "жареный фундук": "Фундук жареный",
    "фундук": "Фундук",
    "арахис": "Арахис",
    "арахисовая паста": "Арахисовая паста",
    "эспрессо": "Эспрессо",
    "амаретто": "Амаретто",
    "мятная эссенция": "Мятная эссенция",
    "корица молотая ": "Корица",
}

SECTION_RE = re.compile(
    r"^(бисквит|крем|корж|коржи|песочная|сырная|заливка|покрытие|муссовая|компоте|"
    r"начинка|глазурь|карамель|ганаш|конфи|дакуаз|сабле|брауни|желе|пралине)",
    re.IGNORECASE,
)
PORTION_RE = re.compile(r"^(bento|бенто|торт|изделие|отвес)\b", re.IGNORECASE)
YIELD_RE = re.compile(r"^выход\b", re.IGNORECASE)
RANGE_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*[–—-]\s*(\d+(?:[.,]\d+)?)"
)
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
SKIP_QTY_RE = re.compile(
    r"кончик|пачк|немного|необходим|чайн|ложек|ложк|красител",
    re.IGNORECASE,
)


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def dec(value: str) -> Decimal:
    return Decimal(value.replace(",", "."))


def qstr(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if rounded < Decimal("0.001"):
        raise RuntimeError(f"quantity below 0.001: {value}")
    return f"{rounded:.3f}".rstrip("0").rstrip(".")


def canon(name: str) -> str:
    cleaned = name.replace("—", " ").replace("–", " ")
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    cleaned = re.sub(r"\b\d+\s*$", " ", cleaned)
    cleaned = re.sub(r"\d+(?:[.,]\d+)?\s*%", " ", cleaned)
    cleaned = re.sub(r"сила\s+\d+\s*bloom", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d+\s*bloom\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"замороженн\w*", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"комнатной температуры", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"холодн\w*", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\d+(?:[.,]\d+)?\s*г\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^для декора\s+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" /.,-")
    key = cleaned.casefold()
    if key.startswith("вода"):
        return "Вода"
    if key.startswith("молоко"):
        return "Молоко"
    if key.startswith("сахар") and not any(word in key for word in ("пудр", "тростник", "коричнев", "ванил")):
        return "Сахар"
    if key in {"мука", "мука пшеничная", "пшеничная мука"}:
        return "Мука пшеничная"
    if key in EXACT_NAMES:
        return EXACT_NAMES[key]
    if cleaned[:1].islower():
        cleaned = cleaned[:1].upper() + cleaned[1:]
    return cleaned


def piece_grams(name: str, count: Decimal) -> tuple[str, Decimal, str]:
    ingredient = canon(re.sub(r"\d+(?:[.,]\d+)?\s*шт\.?", " ", name, flags=re.IGNORECASE))
    if ingredient == "Ксантановая камедь":
        return ingredient, count, f"{ingredient}: в карточке «{count} шт», в составе {qstr(count)} г"
    if ingredient == "Желток":
        return ingredient, count * YOLK_GRAMS, f"{ingredient}: {qstr(count)} шт, {YOLK_NOTE}"
    if ingredient == "Яйцо":
        return ingredient, count * EGG_GRAMS, f"{ingredient}: {qstr(count)} шт, {PIECE_NOTE}"
    raise RuntimeError(f"piece quantity for {name}")


def parse_amount(name: str, raw: str) -> tuple[list[tuple[str, Decimal, str]], list[str]]:
    text = raw.strip()
    notes: list[str] = []
    if not text:
        return [], notes
    if SKIP_QTY_RE.search(text) or SKIP_QTY_RE.search(name):
        notes.append(f"Без строки состава: {name.strip()} — {text}")
        return [], notes
    slash = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)", text)
    if slash and "/" in name:
        left, right = [part.strip() for part in name.split("/", 1)]
        return [
            (canon(left), dec(slash.group(1)), "g"),
            (canon(right), dec(slash.group(2)), "g"),
        ], [f"{name.strip()}: в карточке {text}"]
    if "шт" in text.casefold() or "шт" in name.casefold():
        match = NUMBER_RE.search(text) or NUMBER_RE.search(name)
        if match is None:
            raise RuntimeError(f"piece count missing: {name} / {text}")
        ingredient, quantity, note = piece_grams(name, dec(match.group(0)))
        return [(ingredient, quantity, "g")], [note]
    found = RANGE_RE.search(text)
    if found:
        start = dec(found.group(1))
        end = dec(found.group(2))
        middle = (start + end) / 2
        return [(canon(name), middle, "g")], [f"{canon(name)}: в карточке {text.strip()}, в составе {qstr(middle)} г"]
    match = NUMBER_RE.search(text)
    if match is None:
        notes.append(f"Без строки состава: {name.strip()} — {text}")
        return [], notes
    quantity = dec(match.group(0))
    note = ""
    if re.search(r"примерно|около", text, re.IGNORECASE):
        note = f"{canon(name)}: в карточке {text.strip()}"
    notes_out = [note] if note else []
    return [(canon(name), quantity, "g")], notes_out


def is_section(name: str) -> bool:
    stripped = name.strip()
    if not stripped:
        return False
    if stripped.endswith(":"):
        return True
    if PORTION_RE.match(stripped) or YIELD_RE.match(stripped):
        return True
    if re.fullmatch(r"\d+\s*шт\.?", stripped, re.IGNORECASE):
        return True
    letters = [char for char in stripped if char.isalpha()]
    if letters and all(char.isupper() for char in letters) and len(stripped) < 40:
        return True
    return bool(SECTION_RE.match(stripped))


def cell_value(buffer: bytes, strings: dict[int, str]) -> str:
    if not buffer:
        return ""
    if buffer[0] != 5:
        raise RuntimeError(f"cell storage version {buffer[0]}")
    cell_type = buffer[1]
    flags = unpack("<i", buffer[8:12])[0]
    offset = 12
    number = None
    if flags & 0x1:
        number = _unpack_decimal128(buffer[offset : offset + 16])
        offset += 16
    if flags & 0x2:
        offset += 8
    if flags & 0x4:
        offset += 8
    string_id = None
    if flags & 0x8:
        string_id = unpack("<i", buffer[offset : offset + 4])[0]
    if cell_type == TST.numberCellType:
        return str(number)
    if cell_type == TST.textCellType:
        if string_id is None:
            raise RuntimeError("text cell without string id")
        if string_id not in strings:
            raise RuntimeError(f"missing string {string_id}")
        return strings[string_id]
    if cell_type in (TST.genericCellType, TST.automaticCellType):
        return ""
    raise RuntimeError(f"cell type {cell_type}")


def pages_tables(path: Path) -> list[list[tuple[str, str, str]]]:
    archive = zipfile.ZipFile(path)
    strings: dict[int, str] = {}
    tiles = []
    for name in archive.namelist():
        if not name.endswith(".iwa"):
            continue
        if "DataList" not in name and "Tile" not in name:
            continue
        iwa = IWAFile.from_buffer(archive.read(name), name)
        for chunk in iwa.chunks:
            for segment in chunk.archives:
                for obj in segment.objects:
                    if type(obj).__name__ == "TableDataList" and obj.listType == 1:
                        for entry in obj.entries:
                            if entry.string and "\x08" not in entry.string:
                                strings[entry.key] = entry.string
                    if type(obj).__name__ == "Tile" and obj.rowInfos:
                        tiles.append(obj)
    tables = []
    for tile in tiles:
        rows = []
        for info in tile.rowInfos:
            buffers = get_storage_buffers_for_row(
                info.cell_storage_buffer,
                info.cell_offsets,
                8,
                info.has_wide_offsets,
            )
            values = [cell_value(buffer, strings) if buffer else "" for buffer in buffers]
            while len(values) < 3:
                values.append("")
            if any(value.strip() for value in values[:3]):
                rows.append((values[0].strip(), values[1].strip(), values[2].strip()))
        tables.append(rows)
    return tables


def rows_to_parts(rows: list[tuple[str, str, str]]) -> tuple[list[dict], list[str], Decimal | None]:
    lines: list[dict] = []
    notes: list[str] = []
    methods: list[str] = []
    yield_override = None
    for name, qty, method in rows:
        if method.strip():
            methods.append(method.strip())
        header = name.casefold() in {"", "ингредиент", "ингридиенты"} and (
            qty.casefold().startswith("кол-во") or name.casefold() in {"ингредиент", "ингридиенты"}
        )
        if header and not qty.replace(".", "", 1).isdigit():
            continue
        if name.casefold() in {"ингредиент", "ингридиенты"}:
            continue
        if qty.casefold().startswith("кол-во"):
            continue
        label = name.strip()
        amount = qty.strip()
        if YIELD_RE.match(label) or (not label and YIELD_RE.match(amount)):
            source = label or amount
            if RANGE_RE.search(source):
                notes.append(source)
            else:
                match = NUMBER_RE.search(source)
                if match is None:
                    notes.append(source)
                else:
                    quantity = dec(match.group(0))
                    if "кг" in source.casefold():
                        quantity *= 1000
                    yield_override = quantity
                    notes.append(source)
            continue
        if PORTION_RE.match(label):
            notes.append(f"{label}: {amount}".strip(": "))
            continue
        if not label:
            if amount:
                notes.append(amount)
            continue
        if is_section(label) and not amount:
            notes.append(label.rstrip(":"))
            continue
        parsed, parsed_notes = parse_amount(label, amount)
        notes.extend(parsed_notes)
        if not parsed and not amount:
            notes.append(f"Без веса: {label}")
            continue
        for ingredient, quantity, unit in parsed:
            lines.append({"ingredient": ingredient, "quantity": qstr(quantity), "loss_percent": "0", "unit": unit})
    method = "\n".join(dict.fromkeys(notes + methods))
    return lines, [method] if method else [], yield_override


def component_line(name: str, quantity: Decimal, unit: str) -> dict:
    return {"ingredient": name, "quantity": qstr(quantity), "loss_percent": "0", "unit": unit}


def semi_line(name: str, quantity: Decimal) -> dict:
    return {"semi_product": name, "quantity": qstr(quantity), "loss_percent": "0"}


def yield_of(lines: list[dict]) -> str:
    total = sum(Decimal(row["quantity"]) for row in lines)
    return qstr(total)


def slug(name: str) -> str:
    cleaned = re.sub(r"[^\w]+", "-", nfc(name).casefold(), flags=re.UNICODE).strip("-")
    return cleaned or "image"


def copy_preview(path: Path, name: str, used: set[str]) -> list[str]:
    archive = zipfile.ZipFile(path)
    if "preview.jpg" not in archive.namelist():
        return []
    stem = slug(name)
    filename = f"{stem}.jpg"
    index = 2
    while filename in used:
        filename = f"{stem}-{index}.jpg"
        index += 1
    used.add(filename)
    target = IMAGES / filename
    target.write_bytes(archive.read("preview.jpg"))
    return [f"images/{filename}"]


def skip_pages(name: str) -> bool:
    folded = nfc(name).casefold()
    if "начинки тортов" in folded:
        return True
    if folded.startswith("sweet_chill"):
        return True
    if folded.startswith("техкарта") and ("лайм" in folded or "малина" in folded):
        return True
    return False


def milk_girl(filename: str, lines: list[dict], method: str, images: list[str]) -> dict:
    folded = nfc(filename).casefold()
    if "1,5" in folded or "1.5" in folded:
        basis = "1.5"
        title = "Молочная девочка 1,5 кг"
    elif "2,5" in folded or "2.5" in folded:
        basis = "2.5"
        title = "Молочная девочка 2,5 кг"
    else:
        basis = "2"
        title = "Молочная девочка 2 кг"
    method = "Конфи клубничное — по рецепту полуфабриката, вес в этой карточке не указан.\n" + method
    return {
        "name": title,
        "kind": "weighted",
        "basis_weight_kg": basis,
        "category": "Торты",
        "method": method.strip(),
        "images": images,
        "lines": [{key: value for key, value in row.items() if key != "unit"} for row in lines],
    }


def cupcakes(rows: list[tuple[str, str, str]], method_bits: list[str], images: list[str]) -> dict:
    batch: list[dict] = []
    cream: list[dict] = []
    notes: list[str] = []
    phase = ""
    for name, qty, method in rows:
        if method.strip():
            method_bits.append(method.strip())
        label = name.strip()
        if re.fullmatch(r"5\s*шт\.?", label, re.IGNORECASE):
            phase = "skip"
            continue
        if re.fullmatch(r"10\s*шт\.?", label, re.IGNORECASE):
            phase = "batch"
            continue
        if "капкейк" in label.casefold():
            phase = "cream"
            continue
        if phase == "" or phase == "skip":
            continue
        parsed, parsed_notes = parse_amount(label, qty)
        notes.extend(parsed_notes)
        target = batch if phase == "batch" else cream
        for ingredient, quantity, unit in parsed:
            amount = quantity / Decimal("10") if phase == "batch" else quantity
            target.append(component_line(ingredient, amount, unit))
    method = (
        "Расчёт на 1 капкейк. Тесто взято из колонки на 10 шт и разделено на 10. "
        "Колонка на 5 шт в составе не дублируется.\n"
        + "\n".join(dict.fromkeys(notes + method_bits))
    )
    return {
        "name": "Капкейки",
        "kind": "piece",
        "basis_weight_kg": None,
        "category": "Пирожные",
        "method": method.strip(),
        "images": images,
        "lines": [{key: value for key, value in row.items() if key != "unit"} for row in batch + cream],
    }


def cream_cheese(rows: list[tuple[str, str, str]], images: list[str]) -> dict:
    lines: list[dict] = []
    notes: list[str] = ["В составе партия на торт 1,5 кг, выход 470 г. Остальные размеры ниже."]
    capture = False
    for name, qty, method in rows:
        label = name.strip()
        amount = qty.strip()
        if method.strip():
            notes.append(method.strip())
        if label or amount:
            notes.append(f"{label}: {amount}".strip(": "))
        if label.casefold().startswith("торт 1,5") or label.casefold().startswith("торт 1.5"):
            capture = True
            lines = []
            continue
        if capture and (label.casefold().startswith("торт") or YIELD_RE.match(amount) or YIELD_RE.match(label)):
            if YIELD_RE.match(amount) or YIELD_RE.match(label):
                capture = False
            continue
        if not capture or not label:
            continue
        parsed, _notes = parse_amount(label, amount)
        for ingredient, quantity, unit in parsed:
            lines.append(component_line(ingredient, quantity, unit))
    return {
        "name": "Кремчиз на масле",
        "unit": "g",
        "yield_quantity": "470",
        "method": "\n".join(dict.fromkeys(notes)),
        "images": images,
        "lines": [{key: value for key, value in row.items() if key != "unit"} for row in lines],
    }


def decor(rows: list[tuple[str, str, str]], images: list[str]) -> list[dict]:
    ganache_method = []
    velour_method = []
    other = []
    for name, qty, method in rows:
        label = name.strip()
        if label.casefold().startswith("декор"):
            continue
        block = "\n".join(part for part in (label, qty, method) if part.strip())
        if label.casefold().startswith("ганаш"):
            ganache_method.append(block)
        elif label.casefold().startswith("велюр"):
            velour_method.append(block)
        else:
            other.append(block)
    ganache_lines = [
        component_line("Белый шоколад", Decimal("500"), "g"),
        component_line("Сливки 33%", Decimal("180"), "g"),
        component_line("Масло сливочное", Decimal("230"), "g"),
        component_line("Глюкозный сироп", Decimal("57"), "g"),
    ]
    velour_lines = [
        component_line("Белый шоколад", Decimal("100"), "g"),
        component_line("Какао-масло", Decimal("100"), "g"),
    ]
    ganache_text = "\n".join(ganache_method + ["Другие приёмы декора:"] + other)
    return [
        {
            "name": "Ганаш для торта 20 см",
            "unit": "g",
            "yield_quantity": yield_of(ganache_lines),
            "method": ganache_text,
            "images": images,
            "lines": [{key: value for key, value in row.items() if key != "unit"} for row in ganache_lines],
        },
        {
            "name": "Велюр",
            "unit": "g",
            "yield_quantity": yield_of(velour_lines),
            "method": "\n".join(velour_method),
            "images": [],
            "lines": [{key: value for key, value in row.items() if key != "unit"} for row in velour_lines],
        },
    ]


def napoleon(rows: list[tuple[str, str, str]], images: list[str]) -> tuple[dict, dict]:
    phase = ""
    custard: list[dict] = []
    card: list[dict] = []
    notes: list[str] = ["Рецепт на 1 торт, вес в файле не указан."]
    for name, qty, method in rows:
        if method.strip():
            notes.append(method.strip())
        label = name.strip()
        if "заварн" in label.casefold() and not qty.strip():
            phase = "custard"
            notes.append(label)
            continue
        if "дипломат" in label.casefold():
            phase = "diplomat"
            notes.append(label)
            continue
        if is_section(label) and not qty.strip():
            phase = "cake"
            notes.append(label)
            continue
        parsed, parsed_notes = parse_amount(label, qty)
        notes.extend(parsed_notes)
        if phase == "custard":
            for ingredient, quantity, unit in parsed:
                custard.append(component_line(ingredient, quantity, unit))
            continue
        if label.casefold().startswith("заварной крем"):
            card.append(semi_line("Заварной крем", Decimal(parsed[0][1]) if parsed else Decimal(qty)))
            continue
        for ingredient, quantity, unit in parsed:
            card.append(component_line(ingredient, quantity, unit))
    semi = {
        "name": "Заварной крем",
        "unit": "g",
        "yield_quantity": yield_of(custard),
        "method": "Партия заварного крема из техкарты «Наполеон».",
        "images": [],
        "lines": [{key: value for key, value in row.items() if key != "unit"} for row in custard],
    }
    card_body = {
        "name": "Наполеон",
        "kind": "piece",
        "basis_weight_kg": None,
        "category": "Торты",
        "method": "\n".join(dict.fromkeys(notes)),
        "images": images,
        "lines": [{key: value for key, value in row.items() if key != "unit"} for row in card],
    }
    return semi, card_body


def semi_from_rows(name: str, rows: list[tuple[str, str, str]], images: list[str]) -> dict:
    lines, methods, yield_override = rows_to_parts(rows)
    if not lines:
        raise RuntimeError(f"no lines in {name}")
    stored = [{key: value for key, value in row.items() if key != "unit"} for row in lines]
    return {
        "name": name,
        "unit": "g",
        "yield_quantity": qstr(yield_override) if yield_override is not None else yield_of(stored),
        "method": "\n".join(methods),
        "images": images,
        "lines": stored,
    }


def piece_from_rows(name: str, category: str, rows: list[tuple[str, str, str]], images: list[str]) -> dict:
    lines, methods, _yield = rows_to_parts(rows)
    if not lines:
        raise RuntimeError(f"no lines in {name}")
    method = "Рецепт на 1 изделие, вес в файле не указан.\n" + "\n".join(methods)
    return {
        "name": name,
        "kind": "piece",
        "basis_weight_kg": None,
        "category": category,
        "method": method.strip(),
        "images": images,
        "lines": [{key: value for key, value in row.items() if key != "unit"} for row in lines],
    }


def pages_name(filename: str) -> str:
    folded = nfc(Path(filename).stem).casefold().replace("_", " ")
    folded = re.sub(r"\s+", " ", folded)
    rules = [
        ("безе", "Безе"),
        ("красный бархат", "Красный бархат"),
        ("постный", "шоколад", "Постный шоколадный бисквит"),
        ("постный", "Постный ванильный бисквит"),
        ("шаблон", "копия 2", "Фундучный бисквит с кремом"),
        ("шаблон", "копия 6", "Вишнёвая начинка"),
        ("ванильный бисквит", "Ванильный бисквит"),
        ("карамель", "Карамель солёная"),
        ("клубничное конфи", "Клубничное конфи"),
        ("конфи малина", "Конфи малина"),
        ("конфи манго", "Конфи манго-маракуйя"),
        ("медовик", "Медовик"),
        ("морковный бисквит", "Морковный бисквит"),
        ("тропический", "Тропический бисквит"),
        ("фисташковый бисквит", "Фисташковый бисквит"),
        ("шоколадный бисквит", "Шоколадный бисквит"),
        ("муссовый манго", "Муссовый торт манго"),
        ("муссовый торт клубника", "Муссовый торт клубника"),
        ("лесные ягоды", "Муссовый торт лесные ягоды"),
        ("ферреро", "Чизкейк Ферреро"),
        ("маракуйя", "Чизкейк маракуйя-манго"),
        ("сникерс", "Чизкейк сникерс"),
        ("яблочный", "Яблочный чизкейк"),
        ("фисташка и малина", "Чизкейк фисташка и малина"),
        ("ягодный", "Ягодный чизкейк"),
    ]
    for rule in rules:
        needles = rule[:-1]
        if all(needle in folded for needle in needles):
            return rule[-1]
    raise RuntimeError(f"unnamed pages file {filename}")


SEMI_TITLES = {
    "Безе",
    "Красный бархат",
    "Постный шоколадный бисквит",
    "Постный ванильный бисквит",
    "Вишнёвая начинка",
    "Ванильный бисквит",
    "Карамель солёная",
    "Клубничное конфи",
    "Конфи малина",
    "Конфи манго-маракуйя",
    "Морковный бисквит",
    "Тропический бисквит",
    "Фисташковый бисквит",
    "Шоколадный бисквит",
}


def pdf_text(path: Path) -> str:
    url = Quartz.NSURL.fileURLWithPath_(str(path))
    document = Quartz.PDFDocument.alloc().initWithURL_(url)
    text = document.string()
    if not text:
        raise RuntimeError(f"empty pdf {path.name}")
    return text


def docx_text(path: Path) -> str:
    archive = zipfile.ZipFile(path)
    root = ElementTree.fromstring(archive.read("word/document.xml"))
    lines = []
    for paragraph in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        bits = [
            node.text or ""
            for node in paragraph.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
        ]
        line = "".join(bits).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def pastry_lines(text: str) -> tuple[list[dict], str, str]:
    count_match = re.search(r"на\s+(\d+)\s+пирож", text, re.IGNORECASE)
    if count_match is None:
        count_match = re.search(r"Выход\s+(\d+)\s*шт", text, re.IGNORECASE)
    if count_match is None:
        raise RuntimeError("pastry piece count missing")
    pieces = Decimal(count_match.group(1))
    weight_match = re.search(r"Вес\s+1\s*шт\.?\s*[~≈]\s*([^\n•]+)", text)
    weight = weight_match.group(1).strip() if weight_match else ""
    raw_lines = [line.strip() for line in text.replace("\x0c", "\n").splitlines()]
    start = next(index for index, line in enumerate(raw_lines) if line.startswith("Состав"))
    body = raw_lines[start + 1 :]
    parsed: list[tuple[str, Decimal, str]] = []
    notes: list[str] = []
    method_lines: list[str] = []
    pending = ""

    def take_pending(quantity: Decimal, unit: str, source: str) -> None:
        nonlocal pending
        if "предварительн" in pending.casefold():
            notes.append(f"Вода бланширования не входит в состав: {pending} — {source}")
            pending = ""
            return
        parsed.append((canon(pending), quantity / pieces, unit))
        pending = ""

    for line in body:
        if not line or line in {"Ингредиент", "Количество", "Ингредиент Количество"}:
            continue
        if "Технологическая карта" in line:
            continue
        gelatin = re.fullmatch(
            r"(\d+(?:[.,]\d+)?)\s*г\s*\+\s*(\d+(?:[.,]\d+)?)\s*г(?:\s+\w+){0,3}\s*вод\w*",
            line,
            re.IGNORECASE,
        )
        if gelatin and pending:
            take_pending(dec(gelatin.group(1)), "g", line)
            parsed.append(("Вода", dec(gelatin.group(2)) / pieces, "g"))
            notes.append(f"Желатин: {line}, на партию из {qstr(pieces)} шт")
            continue
        paired = re.fullmatch(
            r"(.+?)\s+(\d+(?:[.,]\d+)?)\s*г(?:\s*\+\s*(\d+(?:[.,]\d+)?)\s*г(?:\s+\w+){0,3}\s*вод\w*)?",
            line,
            re.IGNORECASE,
        )
        if paired and not re.match(r"^\d+\.", line):
            pending = paired.group(1).strip()
            take_pending(dec(paired.group(2)), "g", line)
            if paired.group(3):
                parsed.append(("Вода", dec(paired.group(3)) / pieces, "g"))
                notes.append(f"Вода к желатину {paired.group(3)} г на партию")
            continue
        pieces_line = re.fullmatch(r"(.+?)\s+(\d+)\s*шт\.?", line, re.IGNORECASE)
        if pieces_line and "шпаж" not in line.casefold():
            pending = pieces_line.group(1).strip()
            take_pending(Decimal(pieces_line.group(2)), "pcs", line)
            continue
        own_qty = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*г", line, re.IGNORECASE)
        if own_qty and pending:
            take_pending(dec(own_qty.group(1)), "g", line)
            continue
        if re.match(r"^\d+\.", line) or len(line) > 90 or line.startswith("•"):
            if pending and not is_section(pending) and not pending.startswith("•"):
                notes.append(f"Без веса: {pending}")
            pending = ""
            method_lines.append(line)
            continue
        vague = (
            "порция" in line.casefold()
            or "ч. л" in line.casefold()
            or "по вкусу" in line.casefold()
            or line.casefold() == "по необходимости"
            or bool(re.fullmatch(r"≈?\s*\d+(?:[.,]\d+)?\s*л\b", line, re.IGNORECASE))
            or (SKIP_QTY_RE.search(line) and len(line) < 80)
        )
        if vague:
            label = f"{pending} — {line}" if pending else line
            notes.append(f"Без строки состава: {label}")
            pending = ""
            continue
        if pending:
            notes.append(f"Без веса: {pending}")
        pending = line
    if pending:
        notes.append(f"Без веса: {pending}")
    if not parsed:
        raise RuntimeError("pastry composition empty")
    lines = [component_line(name, quantity, unit) for name, quantity, unit in parsed]
    header = f"Расчёт на {qstr(pieces)} шт"
    if weight:
        header += f", около {weight}"
    header += ". Количества в составе — на 1 шт."
    method = header + "\n" + "\n".join(notes + method_lines)
    return lines, method, qstr(pieces)


def pastry_card(title: str, text: str) -> dict:
    lines, method, _pieces = pastry_lines(text)
    return {
        "name": title,
        "kind": "piece",
        "basis_weight_kg": None,
        "category": "Пирожные",
        "method": method.strip(),
        "images": [],
        "lines": [{key: value for key, value in row.items() if key != "unit"} for row in lines],
    }


def scale_lines(rows: list[tuple[str, Decimal]], pieces: Decimal) -> list[dict]:
    return [component_line(name, quantity / pieces, "g") for name, quantity in rows]


def jar_card(name: str, rows: list[tuple[str, Decimal] | dict], method: str) -> dict:
    pieces = Decimal("10")
    lines = []
    for row in rows:
        if isinstance(row, dict):
            lines.append(
                {
                    "semi_product": row["semi_product"],
                    "quantity": qstr(Decimal(row["quantity"]) / pieces),
                    "loss_percent": "0",
                }
            )
        else:
            ingredient, quantity = row
            lines.append(component_line(ingredient, quantity / pieces, "g"))
    return {
        "name": name,
        "kind": "piece",
        "basis_weight_kg": None,
        "category": "Десерты",
        "method": "Расчёт на 10 порций. Количества в составе — на 1 порцию.\n" + method.strip(),
        "images": [],
        "lines": [{key: value for key, value in row.items() if key != "unit"} for row in lines],
    }


def culinart_method(text: str, extra: str) -> str:
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in {"Чем выше уровень мастерства,", "тем дороже мы стоим!"}:
            continue
        if "Академия кулинарного" in line or "culinart" in line.casefold():
            continue
        if "Все права защищены" in line or stripped.startswith("©") or stripped.startswith("каким-либо"):
            continue
        if stripped.startswith("ещё без письменного"):
            continue
        kept.append(line.rstrip())
    body = "\n".join(kept).strip()
    if extra:
        body += "\n" + extra
    return body


def custard_jar() -> dict:
    lines = [
        component_line("Сливки 33%", Decimal("85"), "g"),
        component_line("Молоко", Decimal("85"), "g"),
        component_line("Сахар", Decimal("20"), "g"),
        component_line("Желток", Decimal("40"), "g"),
        component_line("Кукурузный крахмал", Decimal("8"), "g"),
        component_line("Масло сливочное", Decimal("25"), "g"),
    ]
    return {
        "name": "Заварной крем для банок",
        "unit": "g",
        "yield_quantity": yield_of(lines),
        "method": "Заварной крем из карточек «Фундучное наслаждение» и «Экзотический десерт».",
        "images": [],
        "lines": [{key: value for key, value in row.items() if key != "unit"} for row in lines],
    }


def build() -> None:
    if IMAGES.exists():
        shutil.rmtree(IMAGES)
    IMAGES.mkdir(parents=True)
    used_images: set[str] = set()
    semis: list[dict] = []
    cards: list[dict] = []
    for filename in sorted(SOURCE.iterdir()):
        if filename.suffix != ".pages" or skip_pages(filename.name):
            continue
        tables = pages_tables(filename)
        rows = [row for table in tables for row in table]
        if not rows:
            raise RuntimeError(f"empty pages {filename.name}")
        folded = nfc(filename.name).casefold()
        if folded.startswith("декоры"):
            semis.extend(decor(rows, []))
            continue
        if "кремчиз" in folded:
            images = copy_preview(filename, "Кремчиз на масле", used_images)
            sheet = IMAGES / "kremchiz-sheet.png"
            shutil.copy(SOURCE / "b0ce358c-c22e-4e69-9866-7e45530f1149.png", sheet)
            images.append("images/kremchiz-sheet.png")
            semis.append(cream_cheese(rows, images))
            continue
        if "капкейк" in folded:
            cards.append(cupcakes(rows, [], copy_preview(filename, "Капкейки", used_images)))
            continue
        if folded.startswith("наполеон"):
            semi, card = napoleon(rows, copy_preview(filename, "Наполеон", used_images))
            semis.append(semi)
            cards.append(card)
            continue
        if "молочная девочка" in folded:
            if "2,кг" in folded:
                continue
            lines, methods, _yield = rows_to_parts(rows)
            title_key = filename.name
            cards.append(
                milk_girl(
                    title_key,
                    lines,
                    "\n".join(methods),
                    copy_preview(filename, pages_name(filename.name) if False else filename.stem, used_images),
                )
            )
            continue
        title = pages_name(filename.name)
        images = copy_preview(filename, title, used_images)
        if title in SEMI_TITLES:
            semis.append(semi_from_rows(title, rows, images))
        else:
            category = "Торты"
            cards.append(piece_from_rows(title, category, rows, images))
    pastry_titles = {
        "Техкарта_корпусные_пирожные_Банан.docx": "Пирожное Банан",
        "Техкарта_корпусные_пирожные_Кофе.docx": "Пирожное Кофе",
        "Техкарта_корпусные_пирожные_Лайм.docx": "Пирожное Лайм",
        "Техкарта_корпусные_пирожные_Малина.docx": "Пирожное Малина",
        "Техкарта_корпусные_пирожные_Манго.docx": "Пирожное Манго",
        "Техкарта_корпусные_пирожные_Персик_жасмин.docx": "Пирожное Персик-жасмин",
        "Техкарта_корпусные_пирожные_Фисташка.docx": "Пирожное Фисташка",
        "Техкарта_корпусные_пирожные_Черника.docx": "Пирожное Черника",
        "Техкарта_корпусные_пирожные_Апельсин.pdf": "Пирожное Апельсин",
        "Техкарта_корпусные_пирожные_Арахис.pdf": "Пирожное Арахис",
    }
    for filename in sorted(SOURCE.iterdir()):
        key = nfc(filename.name)
        title = ""
        for candidate, candidate_title in pastry_titles.items():
            if nfc(candidate) == key:
                title = candidate_title
        if not title:
            continue
        text = docx_text(filename) if filename.suffix == ".docx" else pdf_text(filename)
        cards.append(pastry_card(title, text))
    pdfs = {nfc(path.name): path for path in SOURCE.glob("*.pdf")}
    jars = {
        "Дубай.pdf": (
            "Дубай",
            [
                ("Масло сливочное", Decimal("150")),
                ("Сахар", Decimal("80")),
                ("Сахар тростниковый", Decimal("90")),
                ("Яйцо", Decimal("135")),
                ("Мука пшеничная", Decimal("70")),
                ("Соль", Decimal("2")),
                ("Молочный шоколад", Decimal("120")),
                ("Молочный шоколад", Decimal("150")),
                ("Сливки 33%", Decimal("80")),
                ("Сливки 33%", Decimal("300")),
                ("Желатин", Decimal("4")),
                ("Вода", Decimal("20")),
                ("Молочный шоколад", Decimal("200")),
                ("Сливки 33%", Decimal("200")),
                ("Желатин", Decimal("4")),
                ("Вода", Decimal("20")),
                ("Катаифи", Decimal("225")),
                ("Масло растительное", Decimal("30")),
                ("Белый шоколад", Decimal("100")),
                ("Фисташковая паста", Decimal("200")),
            ],
            "Желатин замочен водой 1:5.",
        ),
        "Твикс.pdf": (
            "Твикс",
            [
                ("Мука пшеничная", Decimal("280")),
                ("Масло сливочное", Decimal("180")),
                ("Миндальная мука", Decimal("52")),
                ("Сахар", Decimal("110")),
                ("Соль", Decimal("7")),
                ("Ванильный экстракт", Decimal("10")),
                ("Яйцо", Decimal("50")),
                ("Молочный шоколад", Decimal("250")),
                ("Сахар", Decimal("120")),
                ("Масло сливочное", Decimal("40")),
                ("Сливки 33%", Decimal("150")),
                ("Соль", Decimal("1")),
                ("Шоколад", Decimal("225")),
                ("Сливки 33%", Decimal("120")),
                ("Сливки 33%", Decimal("450")),
                ("Желатин", Decimal("6")),
                ("Вода", Decimal("30")),
                ("Шоколад", Decimal("200")),
                ("Сливки 33%", Decimal("200")),
                ("Желатин", Decimal("2")),
                ("Вода", Decimal("10")),
            ],
            "Яйцо в сабле: 1 шт = 50 г на всю партию. Желатин замочен водой 1:5.",
        ),
        "Медовик с облепихой.pdf": (
            "Медовик с облепихой",
            [
                ("Масло сливочное", Decimal("50")),
                ("Сахар", Decimal("110")),
                ("Мёд", Decimal("75")),
                ("Сода", Decimal("9")),
                ("Соль", Decimal("1")),
                ("Мука пшеничная", Decimal("310")),
                ("Яйцо", Decimal("85")),
                ("Сок лимона", Decimal("12")),
                ("Сметана 30%", Decimal("320")),
                ("Сливки 33%", Decimal("100")),
                ("Маскарпоне", Decimal("176")),
                ("Мёд", Decimal("50")),
                ("Сахарная пудра", Decimal("50")),
                ("Пюре облепихи", Decimal("360")),
                ("Сахар", Decimal("120")),
                ("Пектин NH", Decimal("12")),
                ("Желатин", Decimal("5")),
                ("Вода", Decimal("25")),
            ],
            "Сметана в карточке указана как 25–30%. Желатин замочен водой 1:5.",
        ),
        "Морковный кекс.pdf": (
            "Морковный кекс",
            [
                ("Морковь", Decimal("125")),
                ("Пекан", Decimal("30")),
                ("Изюм", Decimal("30")),
                ("Разрыхлитель", Decimal("4")),
                ("Сода", Decimal("2.5")),
                ("Корица", Decimal("4")),
                ("Соль", Decimal("3")),
                ("Мука пшеничная", Decimal("125")),
                ("Сахар", Decimal("40")),
                ("Сахар тростниковый", Decimal("450")),
                ("Яйцо", Decimal("125")),
                ("Масло растительное", Decimal("105")),
                ("Сливки 33%", Decimal("135")),
                ("Сахарная пудра", Decimal("60")),
                ("Кремчиз", Decimal("250")),
                ("Маскарпоне", Decimal("100")),
                ("Корица", Decimal("2")),
            ],
            "В PDF количества бисквита съехали. Сода 2,5 г стояла на строке муки. "
            "Свободные числа колонки разобраны так: мука 125 г, сахар 40 г, сахар тростниковый 450 г, яйцо 125 г. "
            "Однозначно читались морковь 125, пекан 30, изюм 30, разрыхлитель 4, корица 4, соль 3, масло 105, "
            "сливки 135, пудра 60, кремчиз 250, маскарпоне 100, корица крема 2.",
        ),
        "Фундучное наслаждение.pdf": (
            "Фундучное наслаждение",
            [
                ("Яичный белок", Decimal("75")),
                ("Сахар", Decimal("25")),
                ("Сахарная пудра", Decimal("60")),
                ("Миндальная мука", Decimal("60")),
                ("Фундучное пралине", Decimal("15")),
                ("Сахар", Decimal("120")),
                ("Сливки 33%", Decimal("150")),
                ("Масло сливочное", Decimal("40")),
                ("Соль", Decimal("1")),
                {"semi_product": "Заварной крем для банок", "quantity": "250"},
                ("Фундучное пралине", Decimal("100")),
                ("Сливки 33%", Decimal("600")),
                ("Желатин", Decimal("5")),
                ("Вода", Decimal("25")),
                ("Молочный шоколад", Decimal("100")),
                ("Сливки 33%", Decimal("100")),
            ],
            "Заварной крем вынесен в полуфабрикат и в мусс входит строкой 250 г на партию. Желатин замочен водой 1:5.",
        ),
        "Эксзотический десерт.pdf": (
            "Экзотический десерт",
            [
                ("Сахарная пудра", Decimal("125")),
                ("Миндальная мука", Decimal("25")),
                ("Кокосовая стружка", Decimal("125")),
                ("Яичный белок", Decimal("150")),
                ("Сахар", Decimal("50")),
                ("Пюре манго", Decimal("360")),
                ("Пюре маракуйи", Decimal("90")),
                ("Сахар", Decimal("90")),
                ("Желатин", Decimal("9")),
                ("Вода", Decimal("45")),
                {"semi_product": "Заварной крем для банок", "quantity": "250"},
                ("Пюре кокоса", Decimal("250")),
                ("Сливки 33%", Decimal("250")),
            ],
            "Заварной крем вынесен в полуфабрикат и в кокосовый крем входит строкой 250 г на партию. "
            "Желатин желе замочен водой 1:5. Конфи в сборке — это желе манго-маракуйя.",
        ),
    }
    semis.append(custard_jar())
    for filename, (title, rows, extra) in jars.items():
        path = pdfs[nfc(filename)]
        cards.append(jar_card(title, rows, culinart_method(pdf_text(path), extra)))
    ingredients: dict[str, str] = {}
    for collection in (semis, cards):
        for entity in collection:
            for row in entity["lines"]:
                if "ingredient" not in row:
                    continue
                unit = "g"
                ingredients.setdefault(row["ingredient"], unit)
    for card in cards:
        for row in card["lines"]:
            if row.get("ingredient") == "Хвостик мандарина":
                ingredients["Хвостик мандарина"] = "pcs"
    payload = {
        "categories": [
            {"name": "Торты", "position": 0},
            {"name": "Пирожные", "position": 1},
            {"name": "Десерты", "position": 2},
        ],
        "ingredients": [{"name": name, "unit": unit} for name, unit in sorted(ingredients.items())],
        "semi_products": semis,
        "tech_cards": cards,
    }
    names = [row["name"] for row in semis + cards]
    if len(names) != len(set(names)):
        raise RuntimeError(f"duplicate names {[name for name in names if names.count(name) > 1]}")
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "tech_cards.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"semis {len(semis)} cards {len(cards)} ingredients {len(ingredients)}")
    for entity in semis:
        print(f"SEMI {entity['name']} yield {entity['yield_quantity']} lines {len(entity['lines'])}")
    for entity in cards:
        basis = entity["basis_weight_kg"] or "-"
        print(f"CARD {entity['kind']} {basis} {entity['name']} lines {len(entity['lines'])}")


if __name__ == "__main__":
    build()
