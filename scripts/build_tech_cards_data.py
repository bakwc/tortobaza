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


def md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def heading_title(value: str) -> str:
    title = value.strip().rstrip(":").strip()
    letters = [char for char in title if char.isalpha()]
    if letters and all(char.isupper() for char in letters):
        return title[:1] + title[1:].lower()
    return title


def is_method_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 40:
        return False
    if stripped.casefold().rstrip(":") in {"метод приготовления", "ингредиенты", "ингридиенты"}:
        return False
    if stripped.endswith(":") and len(stripped.split()) <= 3 and not stripped[0].isdigit():
        return True
    letters = [char for char in stripped if char.isalpha()]
    return bool(letters) and all(char.isupper() for char in letters) and len(letters) > 2


def join_wraps(text: str) -> str:
    out: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf:
            out.append(buf)
            buf = ""

    for raw in text.replace("\u2028", "\n").splitlines():
        line = raw.strip()
        if not line:
            flush()
            if out and out[-1] != "":
                out.append("")
            continue
        if is_method_heading(line):
            flush()
            out.append(line)
            continue
        if not buf:
            buf = line
            continue
        if buf[-1] in ",;:—-" or not line[0].isupper():
            buf = f"{buf} {line}"
            continue
        flush()
        buf = line
    flush()
    cleaned: list[str] = []
    for line in out:
        if line == "" and (not cleaned or cleaned[-1] == ""):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def format_steps(text: str, heading_marks: str) -> str:
    blocks: list[str] = []
    steps: list[str] = []
    bullets: list[str] = []

    def flush() -> None:
        if bullets:
            blocks.append("\n".join(f"- {item}" for item in bullets))
            bullets.clear()
        if not steps:
            return
        cleaned = [re.sub(r"^\d+\.\s*", "", step).strip() for step in steps]
        if len(cleaned) == 1:
            blocks.append(cleaned[0])
        else:
            blocks.append("\n".join(f"{index}. {step}" for index, step in enumerate(cleaned, 1)))
        steps.clear()

    for line in join_wraps(text).splitlines():
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped.casefold() == "метод приготовления":
            continue
        if stripped.startswith("*"):
            if steps:
                flush()
            bullets.append(stripped.lstrip("* ").strip())
            continue
        if is_method_heading(stripped):
            flush()
            blocks.append(f"{heading_marks} {heading_title(stripped)}")
            continue
        if bullets:
            flush()
        steps.append(stripped)
    flush()
    return "\n\n".join(blocks)


def notes_md(notes: list[str]) -> str:
    unique = list(dict.fromkeys(note.strip() for note in notes if note.strip()))
    if not unique:
        return ""
    return "## Примечания\n\n" + "\n".join(f"- {note}" for note in unique)


def portions_md(rows: list[tuple[str, str]]) -> str:
    if not rows:
        return ""
    lines = ["## Отвесы", "", "| Изделие | Отвес |", "| --- | --- |"]
    for name, amount in rows:
        lines.append(f"| {md_cell(name)} | {md_cell(amount)} |")
    return "\n".join(lines)


def assemble_method(body: str, portions: list[tuple[str, str]], notes: list[str]) -> str:
    parts = [part.strip() for part in (body, portions_md(portions), notes_md(notes)) if part.strip()]
    return "\n\n".join(parts)


def add_notes(method: str, extra: list[str]) -> str:
    items = [note.strip() for note in extra if note.strip()]
    if not items:
        return method.strip()
    bullets = "\n".join(f"- {note}" for note in items)
    if "## Примечания" in method:
        return method.rstrip() + "\n" + bullets
    if method.strip():
        return method.strip() + "\n\n## Примечания\n\n" + bullets
    return "## Примечания\n\n" + bullets


def without_unit(rows: list[dict]) -> list[dict]:
    return [{key: value for key, value in row.items() if key != "unit"} for row in rows]


def fold_section_methods(method: str, sections: list[dict]) -> str:
    chunks = [
        f"### {section['name']}\n\n{section['method'].strip()}"
        for section in sections
        if section["method"].strip()
    ]
    if not chunks:
        return method
    block = "\n\n".join(chunks)
    if not method.strip():
        return block
    indexes = [method.find(heading) for heading in ("## Отвесы", "## Примечания")]
    indexes = [index for index in indexes if index != -1]
    if not indexes:
        return method.rstrip() + "\n\n" + block
    marker = min(indexes)
    return method[:marker].rstrip() + "\n\n" + block + "\n\n" + method[marker:]


def card_sections(sections: list[dict]) -> list[dict]:
    return [
        {"name": section["name"], "method": section["method"], "lines": without_unit(section["lines"])}
        for section in sections
    ]


def rows_to_parts(rows: list[tuple[str, str, str]]) -> tuple[list[dict], list[dict], str, Decimal | None]:
    lines: list[dict] = []
    notes: list[str] = []
    portions: list[tuple[str, str]] = []
    section_order: list[str] = []
    section_text: dict[str, list[str]] = {}
    section_lines: dict[str, list[dict]] = {}
    loose: list[str] = []
    current = ""
    yield_override = None

    def push_method(text: str) -> None:
        cleaned = text.strip()
        if not cleaned or cleaned.casefold() == "метод приготовления":
            return
        kept: list[str] = []
        assembly: list[str] = []
        for line in cleaned.splitlines():
            if assembly or (
                is_method_heading(line.strip()) and heading_title(line).casefold() == "сборка"
            ):
                assembly.append(line)
                continue
            kept.append(line)
        if assembly:
            loose.append("\n".join(assembly).strip())
        body = "\n".join(kept).strip()
        if not body:
            return
        if current:
            section_text.setdefault(current, []).append(body)
            if current not in section_order:
                section_order.append(current)
            return
        loose.append(body)

    for name, qty, method in rows:
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
        if is_section(label) and not amount:
            current = label.rstrip(":").strip()
            if current not in section_order:
                section_order.append(current)
            push_method(method)
            continue
        push_method(method)
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
            continue
        if PORTION_RE.match(label):
            if label.casefold() not in {"изделие", "отвес"}:
                portions.append((label, amount))
            continue
        if not label:
            if amount:
                notes.append(amount)
            continue
        parsed, parsed_notes = parse_amount(label, amount)
        notes.extend(parsed_notes)
        if not parsed and not amount:
            notes.append(f"Без веса: {label}")
            continue
        for ingredient, quantity, unit in parsed:
            line = {"ingredient": ingredient, "quantity": qstr(quantity), "loss_percent": "0", "unit": unit}
            if current:
                section_lines.setdefault(current, []).append(line)
                if current not in section_order:
                    section_order.append(current)
            else:
                lines.append(line)
    loose_body = format_steps("\n".join(loose), "###") if loose else ""
    sections: list[dict] = []
    for title in section_order:
        body = format_steps("\n".join(section_text.get(title, [])), "####")
        grouped = section_lines.get(title, [])
        if not body and not grouped:
            continue
        sections.append({"name": heading_title(title), "method": body, "lines": grouped})
    return lines, sections, assemble_method(loose_body, portions, notes), yield_override


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


def milk_girl(filename: str, lines: list[dict], sections: list[dict], method: str, images: list[str]) -> dict:
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
    method = add_notes(method, ["Конфи клубничное — по рецепту полуфабриката, вес в этой карточке не указан."])
    return {
        "name": title,
        "kind": "weighted",
        "basis_weight_kg": basis,
        "basis_quantity": None,
        "category": "Торты",
        "method": method.strip(),
        "images": images,
        "lines": without_unit(lines),
        "sections": card_sections(sections),
    }


def cupcakes(rows: list[tuple[str, str, str]], method_bits: list[str], images: list[str]) -> dict:
    batch: list[dict] = []
    cream: list[dict] = []
    notes: list[str] = []
    phase = ""
    for name, qty, method in rows:
        if method.strip() and method.strip().casefold() != "метод приготовления":
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
            amount = quantity if phase == "batch" else quantity * Decimal("10")
            target.append(component_line(ingredient, amount, unit))
    method = add_notes(
        format_steps("\n\n".join(method_bits), "###"),
        [
            "Расчёт на 10 капкейков. Тесто взято из колонки на 10 шт. "
            "Крем из колонки на 1 капкейк умножен на 10. Колонка на 5 шт в составе не дублируется.",
            *notes,
        ],
    )
    return {
        "name": "Капкейки",
        "kind": "piece",
        "basis_weight_kg": None,
        "basis_quantity": 10,
        "category": "Пирожные",
        "method": method.strip(),
        "images": images,
        "lines": without_unit(batch + cream),
        "sections": [],
    }


def cream_cheese(rows: list[tuple[str, str, str]], images: list[str]) -> dict:
    lines: list[dict] = []
    sizes: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    method_parts: list[str] = []
    capture = False
    for name, qty, method in rows:
        label = name.strip()
        amount = qty.strip()
        if method.strip() and method.strip().casefold() != "метод приготовления":
            method_parts.append(method.strip())
        if re.match(r"^(бенто|торт)\b", label, re.IGNORECASE) and not amount:
            current = {"name": label, "cream": "", "butter": "", "sugar": "", "yield": ""}
            sizes.append(current)
            capture = label.casefold().startswith("торт 1,5") or label.casefold().startswith("торт 1.5")
            if capture:
                lines = []
            continue
        if current is not None and not label and amount.casefold().startswith("выход"):
            current["yield"] = re.sub(r"^выход\s*", "", amount, flags=re.IGNORECASE).strip()
            capture = False
            continue
        if current is not None and label:
            folded = label.casefold()
            if "крем" in folded:
                current["cream"] = amount
            elif "масло" in folded:
                current["butter"] = amount
            elif "пудр" in folded or "сахар" in folded:
                current["sugar"] = amount
        if not capture or not label:
            continue
        parsed, _notes = parse_amount(label, amount)
        for ingredient, quantity, unit in parsed:
            lines.append(component_line(ingredient, quantity, unit))
    table = [
        "| Размер | Кремчиз | Масло | Сахарная пудра | Выход |",
        "| --- | --- | --- | --- | --- |",
    ]
    for size in sizes:
        table.append(
            "| "
            + " | ".join(
                md_cell(size[key]) for key in ("name", "cream", "butter", "sugar", "yield")
            )
            + " |"
        )
    method = add_notes(
        format_steps("\n".join(method_parts), "###") + "\n\n" + "\n".join(table),
        ["В составе партия на торт 1,5 кг, выход 470 г."],
    )
    return {
        "name": "Кремчиз на масле",
        "unit": "g",
        "yield_quantity": "470",
        "method": method,
        "images": images,
        "lines": [{key: value for key, value in row.items() if key != "unit"} for row in lines],
    }


def decor(rows: list[tuple[str, str, str]], images: list[str]) -> list[dict]:
    ganache_intro = ""
    ganache_steps = ""
    velour_steps = ""
    velour_size = ""
    other: list[tuple[str, str, str]] = []
    for name, qty, method in rows:
        label = name.strip()
        if label.casefold().startswith("декор"):
            continue
        if label.casefold().startswith("ганаш"):
            ganache_intro = label
            ganache_steps = method.strip()
        elif label.casefold().startswith("велюр"):
            velour_steps = method.strip()
            size = re.match(r"^(на торт[^:]+)", qty.strip(), re.IGNORECASE)
            if size:
                velour_size = size.group(1).strip().capitalize()
        else:
            other.append((label, qty.strip(), method.strip()))
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
    other_blocks = ["## Другие приёмы декора"]
    for title, materials, steps in other:
        block = f"### {title}"
        if materials:
            block += f"\n\n{materials}"
        formatted = format_steps(steps, "####")
        if formatted:
            block += f"\n\n{formatted}"
        other_blocks.append(block)
    ganache_parts = [part for part in (ganache_intro, format_steps(ganache_steps, "###"), "\n\n".join(other_blocks)) if part]
    velour_parts = [part for part in (velour_size, format_steps(velour_steps, "###")) if part]
    return [
        {
            "name": "Ганаш для торта 20 см",
            "unit": "g",
            "yield_quantity": yield_of(ganache_lines),
            "method": "\n\n".join(ganache_parts),
            "images": images,
            "lines": [{key: value for key, value in row.items() if key != "unit"} for row in ganache_lines],
        },
        {
            "name": "Велюр",
            "unit": "g",
            "yield_quantity": yield_of(velour_lines),
            "method": "\n\n".join(velour_parts),
            "images": [],
            "lines": [{key: value for key, value in row.items() if key != "unit"} for row in velour_lines],
        },
    ]


def napoleon(rows: list[tuple[str, str, str]], images: list[str]) -> tuple[dict, dict]:
    phase = ""
    custard: list[dict] = []
    card: list[dict] = []
    notes: list[str] = []
    current = ""
    section_order: list[str] = []
    section_text: dict[str, list[str]] = {}
    section_lines: dict[str, list[dict]] = {}
    loose: list[str] = []

    def push(text: str) -> None:
        cleaned = text.strip()
        if not cleaned or cleaned.casefold() == "метод приготовления":
            return
        if current:
            section_text.setdefault(current, []).append(cleaned)
            if current not in section_order:
                section_order.append(current)
            return
        loose.append(cleaned)

    for name, qty, method in rows:
        label = name.strip()
        if label.casefold() in {"ингредиенты", "ингридиенты"}:
            continue
        if ("заварн" in label.casefold() and not qty.strip()) or (
            "дипломат" in label.casefold() and not qty.strip()
        ) or (is_section(label) and not qty.strip()):
            current = label
            if current not in section_order:
                section_order.append(current)
            push(method)
            if "заварн" in label.casefold():
                phase = "custard"
            elif "дипломат" in label.casefold():
                phase = "diplomat"
            else:
                phase = "cake"
            continue
        push(method)
        parsed, parsed_notes = parse_amount(label, qty)
        notes.extend(parsed_notes)
        if phase == "custard":
            for ingredient, quantity, unit in parsed:
                custard.append(component_line(ingredient, quantity, unit))
            continue
        if label.casefold().startswith("заварной крем"):
            line = semi_line("Заварной крем", Decimal(parsed[0][1]) if parsed else Decimal(qty))
        else:
            line = None
        if line is None:
            for ingredient, quantity, unit in parsed:
                built = component_line(ingredient, quantity, unit)
                if current:
                    section_lines.setdefault(current, []).append(built)
                else:
                    card.append(built)
            continue
        if current:
            section_lines.setdefault(current, []).append(line)
        else:
            card.append(line)
    loose_body = format_steps("\n".join(loose), "###") if loose else ""
    sections: list[dict] = []
    for title in section_order:
        body = format_steps("\n".join(section_text.get(title, [])), "####")
        grouped = section_lines.get(title, [])
        if not body and not grouped:
            continue
        sections.append({"name": heading_title(title), "method": body, "lines": grouped})
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
        "basis_quantity": 1,
        "category": "Торты",
        "method": add_notes(loose_body, ["Рецепт на 1 торт, вес в файле не указан.", *notes]),
        "images": images,
        "lines": without_unit(card),
        "sections": card_sections(sections),
    }
    return semi, card_body


def semi_from_rows(name: str, rows: list[tuple[str, str, str]], images: list[str]) -> dict:
    ungrouped, sections, method, yield_override = rows_to_parts(rows)
    lines = ungrouped + [line for section in sections for line in section["lines"]]
    if not lines:
        raise RuntimeError(f"no lines in {name}")
    stored = without_unit(lines)
    return {
        "name": name,
        "unit": "g",
        "yield_quantity": qstr(yield_override) if yield_override is not None else yield_of(stored),
        "method": fold_section_methods(method, sections),
        "images": images,
        "lines": stored,
    }


def piece_from_rows(name: str, category: str, rows: list[tuple[str, str, str]], images: list[str]) -> dict:
    ungrouped, sections, method, _yield = rows_to_parts(rows)
    if not ungrouped and not any(section["lines"] for section in sections):
        raise RuntimeError(f"no lines in {name}")
    method = add_notes(method, ["Рецепт на 1 изделие, вес в файле не указан."])
    return {
        "name": name,
        "kind": "piece",
        "basis_weight_kg": None,
        "basis_quantity": 1,
        "category": category,
        "method": method.strip(),
        "images": images,
        "lines": without_unit(ungrouped),
        "sections": card_sections(sections),
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


def blank_section(name: str) -> dict:
    return {"name": name, "lines": [], "chunks": [], "steps": [], "bullets": []}


def find_section(sections: list[dict], name: str) -> dict:
    folded = name.casefold()
    for section in sections:
        if section["name"].casefold() == folded:
            return section
    section = blank_section(name)
    sections.append(section)
    return section


def flush_section(section: dict) -> None:
    if section["bullets"]:
        section["chunks"].append("\n".join(f"- {item}" for item in section["bullets"]))
        section["bullets"] = []
    if section["steps"]:
        section["chunks"].append("\n".join(f"{index}. {step}" for index, step in enumerate(section["steps"], 1)))
        section["steps"] = []


def section_payload(sections: list[dict]) -> list[dict]:
    payload = []
    for section in sections:
        flush_section(section)
        method = "\n\n".join(chunk for chunk in section["chunks"] if chunk.strip())
        if not method and not section["lines"]:
            continue
        payload.append({"name": section["name"], "method": method, "lines": section["lines"]})
    return payload


def quantity_lines(name: str, raw: str) -> tuple[list[dict], list[str]]:
    text = raw.strip()
    if "предварительн" in name.casefold():
        return [], [f"Вода бланширования не входит в состав: {name} — {text}"]
    if re.fullmatch(r"≈?\s*\d+(?:[.,]\d+)?\s*л\b", text, re.IGNORECASE):
        return [], [f"Без строки состава: {name} — {text}"]
    if "порция" in text.casefold() or re.search(r"ч\.\s*л|по вкусу", text, re.IGNORECASE):
        return [], [f"Без строки состава: {name} — {text}"]
    embedded = re.search(r"(.+?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*г\b", text, re.IGNORECASE)
    if embedded and not re.match(r"^[≈\d]", text):
        return quantity_lines(embedded.group(1), f"{embedded.group(2)} г")
    gelatin = re.fullmatch(
        r"(\d+(?:[.,]\d+)?)\s*г\s*\+\s*(\d+(?:[.,]\d+)?)\s*г(?:\s+\w+)*",
        text,
        re.IGNORECASE,
    )
    if gelatin and "вод" in text.casefold():
        parsed, notes = parse_amount(name, f"{gelatin.group(1)} г")
        lines = [component_line(ingredient, quantity, unit) for ingredient, quantity, unit in parsed]
        lines.append(component_line("Вода", dec(gelatin.group(2)), "g"))
        notes.append(f"Желатин: {text}")
        return lines, notes
    if "шт" in text.casefold():
        match = NUMBER_RE.search(text)
        if match is None:
            raise RuntimeError(f"piece count missing: {name} / {text}")
        ingredient = canon(name)
        if ingredient not in {"Яйцо", "Желток", "Ксантановая камедь", "Хвостик мандарина"}:
            return [], [f"Без строки состава: {name} — {text}"]
        if ingredient in {"Яйцо", "Желток", "Ксантановая камедь"}:
            parsed, notes = parse_amount(name, text)
            return [component_line(ingredient_name, quantity, unit) for ingredient_name, quantity, unit in parsed], notes
        return [component_line(ingredient, dec(match.group(0)), "pcs")], []
    parsed, notes = parse_amount(name, text)
    return [component_line(ingredient, quantity, unit) for ingredient, quantity, unit in parsed], notes


def piece_count(text: str, path: Path) -> int:
    match = re.search(r"на\s+(\d+)\s+пирож", text, re.IGNORECASE)
    if match is None:
        match = re.search(r"выход\s*(\d+)\s*шт", text, re.IGNORECASE)
    if match is None:
        raise RuntimeError(f"pastry piece count missing in {path.name}")
    return int(match.group(1))


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


def docx_runs(element, word: str) -> str:
    text = "".join(node.text or "" for node in element.iter(f"{word}t"))
    return re.sub(r"([а-яё])([А-ЯЁ])", r"\1 \2", text).strip()


def plain_section_title(text: str) -> str:
    match = re.fullmatch(r"\d+\.\s+(.+)", text)
    if match is None:
        return ""
    title = match.group(1).strip()
    if re.search(r"[.!?]", title) or len(title) > 80:
        return ""
    return title


def docx_pastry_card(title: str, path: Path) -> dict:
    word = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    archive = zipfile.ZipFile(path)
    root = ElementTree.fromstring(archive.read("word/document.xml"))
    body = root.find(f"{word}body")
    sections: list[dict] = []
    notes: list[str] = []
    inventory: list[str] = []
    quality: list[str] = []
    mode = ""
    current: dict | None = None

    def take_rows(rows: list[list[str]], section: dict | None) -> None:
        target = section
        for cells in rows[1:]:
            name = cells[0].strip() if cells else ""
            amount = cells[1].strip() if len(cells) > 1 else ""
            if not name or name.casefold() in {"ингредиент", "количество"}:
                continue
            if not amount:
                target = find_section(sections, name)
                continue
            if target is None:
                notes.append(f"Без строки состава: {name} — {amount}")
                continue
            lines, row_notes = quantity_lines(name, amount)
            notes.extend(row_notes)
            target["lines"].extend(lines)

    for element in list(body):
        tag = element.tag.replace(word, "")
        if tag == "tbl":
            rows = []
            for row in element.findall(f"{word}tr"):
                rows.append([docx_runs(cell, word) for cell in row.findall(f"{word}tc")])
            if len(rows) == 1 and len(rows[0]) == 1 and rows[0][0]:
                quote = rows[0][0]
                if current is not None:
                    flush_section(current)
                    current["chunks"].append(f"> {quote}")
                else:
                    notes.append(quote)
                continue
            header = " ".join(rows[0]).casefold() if rows else ""
            if "ингредиент" in header and "количество" in header:
                take_rows(rows, current if mode == "section" else None)
                continue
            items = [cell.lstrip("• ").strip() for row in rows for cell in row if cell.strip()]
            if mode == "inventory":
                inventory.extend(items)
            elif mode == "quality":
                quality.extend(item.lstrip("• ").strip() for item in items)
            continue
        if tag != "p":
            continue
        style = element.find(f"{word}pPr/{word}pStyle")
        style_name = style.get(f"{word}val") if style is not None else ""
        text = docx_runs(element, word)
        if not text or style_name == "TitleCustom":
            continue
        folded = text.casefold()
        if style_name == "H1Custom" and folded == "состав" or folded in {"состав", "состав изделия"}:
            if current is not None:
                flush_section(current)
            current = None
            mode = "composition"
            continue
        if style_name == "H1Custom" and folded == "инвентарь" or folded == "инвентарь":
            if current is not None:
                flush_section(current)
            current = None
            mode = "inventory"
            continue
        if style_name == "H1Custom" and folded == "контроль качества" or folded == "контроль качества":
            if current is not None:
                flush_section(current)
            current = None
            mode = "quality"
            continue
        titled = text if style_name == "H1Custom" else plain_section_title(text)
        if titled and style_name != "ListBullet":
            if current is not None:
                flush_section(current)
            current = find_section(sections, titled)
            mode = "section"
            continue
        if mode == "inventory" and (style_name == "ListBullet" or text[:1] in {"•", ""}):
            inventory.append(text.lstrip("• ").strip())
            continue
        if mode == "quality":
            quality.append(text.lstrip("• ").strip())
            continue
        if mode != "section" or current is None:
            notes.append(text)
            continue
        numbered = re.match(r"^\d+\.\s*(.*)", text)
        if style_name == "ListBullet" or text[:1] in {"•", ""}:
            flush_section(current)
            current["bullets"].append(text.lstrip("• ").strip())
            continue
        if numbered:
            if current["bullets"]:
                flush_section(current)
            current["steps"].append(numbered.group(1))
            continue
        if current["steps"] and text[:1].islower():
            current["steps"][-1] = f"{current['steps'][-1]} {text}"
            continue
        flush_section(current)
        current["chunks"].append(text)
    if current is not None:
        flush_section(current)
    card_chunks = []
    if inventory:
        card_chunks.append("## Инвентарь\n\n" + "\n".join(f"- {item}" for item in inventory))
    if quality:
        card_chunks.append("## Контроль качества\n\n" + "\n".join(f"- {item}" for item in quality))
    return {
        "name": title,
        "kind": "piece",
        "basis_weight_kg": None,
        "basis_quantity": piece_count(docx_text(path), path),
        "category": "Пирожные",
        "method": add_notes("\n\n".join(card_chunks), notes).strip(),
        "images": [],
        "lines": [],
        "sections": card_sections(section_payload(sections)),
    }


def pdf_lines(path: Path) -> list[str]:
    lines = []
    for raw in pdf_text(path).splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if line and not line.startswith("Технологическая карта"):
            lines.append(line)
    return lines


def pdf_qty_split(line: str) -> tuple[str, str]:
    match = re.search(
        r"\s(\d+(?:[.,]\d+)?\s*г(?:\s*\+\s*\d+(?:[.,]\d+)?\s*г(?:\s+\w+)*)?|\d+\s*шт\.?|по необходимости)$",
        line,
        re.IGNORECASE,
    )
    if match is None:
        return "", ""
    return line[: match.start()].strip(), match.group(1).strip()


def pdf_pastry_card(title: str, path: Path) -> dict:
    lines = pdf_lines(path)
    inventory_at = lines.index("Инвентарь")
    composition_at = lines.index("Состав", inventory_at)
    sections: list[dict] = []
    notes: list[str] = []
    current: dict | None = None
    index = composition_at + 1
    if index < len(lines) and lines[index].casefold().startswith("ингредиент"):
        index += 1
    while index < len(lines) and not re.match(r"^\d+\.\s", lines[index]):
        name, amount = pdf_qty_split(lines[index])
        if name and amount:
            if current is None:
                raise RuntimeError(f"ingredient before a section in {path.name}: {lines[index]}")
            parsed, row_notes = quantity_lines(name, amount)
            notes.extend(row_notes)
            current["lines"].extend(parsed)
        elif lines[index][:1].isupper() and not re.search(r"[.!?]", lines[index]) and len(lines[index]) < 80:
            current = find_section(sections, lines[index])
        else:
            notes.append(lines[index])
        index += 1
    while index < len(lines):
        line = lines[index]
        if line.casefold() == "контроль качества":
            index += 1
            break
        name, _amount = pdf_qty_split(line)
        if (
            current is not None
            and line[:1].islower()
            and not re.match(r"^\d+\.\s", line)
            and not line.startswith("Хранение")
        ):
            if current["steps"]:
                current["steps"][-1] = f"{current['steps'][-1]} {line}"
            else:
                notes.append(line)
            index += 1
            continue
        if line.startswith("Хранение"):
            if current is None:
                raise RuntimeError(f"storage note before a section in {path.name}")
            flush_section(current)
            current["chunks"].append(f"> {line}")
            index += 1
            continue
        numbered = re.match(r"^\d+\.\s*(.*)", line)
        if numbered:
            if current is None:
                raise RuntimeError(f"step before a section in {path.name}")
            if current["bullets"]:
                flush_section(current)
            current["steps"].append(numbered.group(1))
            index += 1
            continue
        if line[:1].isupper() and not re.search(r"[.!?]", line) and len(line) < 80 and not name:
            if current is not None:
                flush_section(current)
            current = find_section(sections, line)
            index += 1
            continue
        if current is not None and current["steps"]:
            current["steps"][-1] = f"{current['steps'][-1]} {line}"
            index += 1
            continue
        notes.append(line)
        index += 1
    quality = [line.lstrip("• ").strip() for line in lines[index:] if line.strip()]
    inventory = [line.lstrip("• ").strip() for line in lines[inventory_at + 1 : composition_at]]
    card_chunks = []
    if inventory:
        card_chunks.append("## Инвентарь\n\n" + "\n".join(f"- {item}" for item in inventory))
    if quality:
        card_chunks.append("## Контроль качества\n\n" + "\n".join(f"- {item}" for item in quality))
    for line in lines[:inventory_at]:
        if line.startswith("Расчёт") or line.startswith("Вес") or line.startswith("Ориентировочный"):
            notes.append(line)
    return {
        "name": title,
        "kind": "piece",
        "basis_weight_kg": None,
        "basis_quantity": piece_count(pdf_text(path), path),
        "category": "Пирожные",
        "method": add_notes("\n\n".join(card_chunks), notes).strip(),
        "images": [],
        "lines": [],
        "sections": card_sections(section_payload(sections)),
    }


def docx_method(path: Path) -> str:
    word = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    archive = zipfile.ZipFile(path)
    root = ElementTree.fromstring(archive.read("word/document.xml"))
    body = root.find(f"{word}body")
    notes: list[str] = []
    chunks: list[str] = []
    bullets: list[str] = []
    steps: list[str] = []
    started = False

    def flush() -> None:
        if bullets:
            chunks.append("\n".join(f"- {item}" for item in bullets))
            bullets.clear()
        if steps:
            chunks.append("\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1)))
            steps.clear()

    for element in list(body):
        tag = element.tag.replace(word, "")
        if tag == "tbl":
            rows = element.findall(f"{word}tr")
            cells = rows[0].findall(f"{word}tc") if rows else []
            if len(rows) == 1 and len(cells) == 1:
                flush()
                text = "".join(node.text or "" for node in element.iter(f"{word}t")).strip()
                if text:
                    chunks.append(f"> {text}")
            continue
        if tag != "p":
            continue
        style = element.find(f"{word}pPr/{word}pStyle")
        style_name = style.get(f"{word}val") if style is not None else ""
        text = "".join(node.text or "" for node in element.iter(f"{word}t")).strip()
        if not text:
            continue
        text = re.sub(r"([а-яё])([А-ЯЁ])", r"\1 \2", text)
        if style_name == "TitleCustom":
            continue
        if style_name == "H1Custom":
            flush()
            started = True
            if text.casefold() != "состав":
                chunks.append(f"## {text}")
            continue
        if not started:
            notes.append(text)
            continue
        if style_name == "ListBullet":
            if steps:
                flush()
            bullets.append(text)
            continue
        numbered = re.match(r"^\d+\.\s*(.*)", text)
        if numbered:
            if bullets:
                flush()
            steps.append(numbered.group(1))
            continue
        if steps and text[:1].islower():
            steps[-1] = f"{steps[-1]} {text}"
            continue
        flush()
        chunks.append(text)
    flush()
    return add_notes("\n\n".join(chunk for chunk in chunks if chunk.strip()), notes)


def pastry_lines(text: str) -> tuple[list[dict], list[str], str]:
    count_match = re.search(r"на\s+(\d+)\s+пирож", text, re.IGNORECASE)
    if count_match is None:
        count_match = re.search(r"Выход\s+(\d+)\s*шт", text, re.IGNORECASE)
    if count_match is None:
        raise RuntimeError("pastry piece count missing")
    pieces = Decimal(count_match.group(1))
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
        parsed.append((canon(pending), quantity, unit))
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
            parsed.append(("Вода", dec(gelatin.group(2)), "g"))
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
                parsed.append(("Вода", dec(paired.group(3)), "g"))
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
    return lines, notes, qstr(pieces)


def pastry_card(title: str, text: str, method: str) -> dict:
    lines, notes, pieces = pastry_lines(text)
    return {
        "name": title,
        "kind": "piece",
        "basis_weight_kg": None,
        "basis_quantity": int(pieces),
        "category": "Пирожные",
        "method": add_notes(method, notes),
        "images": [],
        "lines": without_unit(lines),
        "sections": [],
    }


def split_method_chapters(method: str) -> tuple[list[tuple[str, str]], str]:
    chapters: list[tuple[str, str]] = []
    rest: list[str] = []
    for part in re.split(r"\n(?=#{2,3} )", method.strip()):
        if part.startswith("### "):
            title, _sep, body = part.partition("\n")
            chapters.append((title.removeprefix("### ").strip(), body.strip()))
            continue
        if part.strip():
            rest.append(part.strip())
    if not chapters:
        raise RuntimeError("jar method has no chapters")
    return chapters, "\n\n".join(rest)


def jar_line(row: tuple[str, Decimal] | dict) -> dict:
    if isinstance(row, dict):
        return {
            "semi_product": row["semi_product"],
            "quantity": qstr(Decimal(row["quantity"])),
            "loss_percent": "0",
        }
    ingredient, quantity = row
    return component_line(ingredient, quantity, "g")


def jar_card(name: str, grouped: list[tuple[str, list[tuple[str, Decimal] | dict]]], method: str) -> dict:
    chapters, rest = split_method_chapters(method)
    pending = {title: rows for title, rows in grouped}
    if len(pending) != len(grouped):
        raise RuntimeError(f"duplicate section in {name}")
    sections = []
    for title, body in chapters:
        rows = pending.pop(title) if title in pending else None
        lines = [] if rows is None else [jar_line(row) for row in rows]
        sections.append({"name": title, "method": body, "lines": without_unit(lines)})
    if pending:
        raise RuntimeError(f"{name}: sections missing from method: {', '.join(pending)}")
    return {
        "name": name,
        "kind": "piece",
        "basis_weight_kg": None,
        "basis_quantity": 10,
        "category": "Десерты",
        "method": add_notes(rest, ["Расчёт на 10 порций."]),
        "images": [],
        "lines": [],
        "sections": sections,
    }


def pdf_rows(path: Path) -> list[tuple[int, float, float, str]]:
    url = Quartz.NSURL.fileURLWithPath_(str(path))
    document = Quartz.PDFDocument.alloc().initWithURL_(url)
    if document is None:
        raise RuntimeError(f"empty pdf {path.name}")
    rows: list[tuple[int, float, float, str]] = []
    for index in range(document.pageCount()):
        page = document.pageAtIndex_(index)
        selection = page.selectionForRect_(page.boundsForBox_(Quartz.kPDFDisplayBoxMediaBox))
        if selection is None:
            continue
        for line in selection.selectionsByLine():
            text = (line.string() or "").replace("\u2028", " ").strip()
            if not text:
                continue
            bounds = line.boundsForPage_(page)
            rows.append((index, float(bounds.origin.y), float(bounds.origin.x), text))
    if not rows:
        raise RuntimeError(f"empty pdf {path.name}")
    return rows


def skip_culinart_line(text: str) -> bool:
    stripped = text.strip()
    if stripped in {"Чем выше уровень мастерства,", "тем дороже мы стоим!"}:
        return True
    if "Академия кулинарного" in stripped or "culinart" in stripped.casefold():
        return True
    if "Все права защищены" in stripped or stripped.startswith("©") or stripped.startswith("каким-либо"):
        return True
    if stripped.startswith("ещё без письменного") or stripped.startswith("+7"):
        return True
    return False


def culinart_method(path: Path, extra: str) -> str:
    rows = [row for row in pdf_rows(path) if not skip_culinart_line(row[3])]
    method_header = next(row for row in rows if row[3].casefold() == "метод приготовления")
    page, _y, header_x, _text = method_header
    method_lines = [
        row
        for row in rows
        if row[0] == page and header_x - 50 <= row[2] < header_x + 40 and row[3].casefold() != "метод приготовления"
    ]
    method_lines.sort(key=lambda row: row[1], reverse=True)
    sections = []
    qty_ys = [row[1] for row in rows if row[0] == page and 180 <= row[2] <= 280 and re.fullmatch(r"[\d.,]+", row[3])]
    for row_page, y, x, text in rows:
        if row_page != page or x > 160:
            continue
        if text.casefold() in {"ингредиенты", "кол-во/г"}:
            continue
        if re.search(r"\d", text):
            continue
        if any(abs(y - qty_y) <= 3 for qty_y in qty_ys):
            continue
        sections.append((y, heading_title(text)))
    sections.sort(key=lambda row: row[0], reverse=True)
    if not sections:
        raise RuntimeError(f"no method sections in {path.name}")
    paragraphs: list[list[str]] = [[]]
    for index, row in enumerate(method_lines):
        if index and method_lines[index - 1][1] - row[1] >= 20:
            paragraphs.append([])
        paragraphs[-1].append(row[3])
    while len(paragraphs) > len(sections):
        shortest = min(range(len(paragraphs)), key=lambda item: (len(paragraphs[item]), item))
        target = 1 if shortest == 0 else shortest - 1
        if shortest == 0:
            paragraphs[1] = paragraphs[0] + paragraphs[1]
            del paragraphs[0]
        else:
            paragraphs[target].extend(paragraphs[shortest])
            del paragraphs[shortest]
    if len(paragraphs) == len(sections):
        assigned = paragraphs
    else:
        assigned = [[] for _section in sections]
        current = 0
        for index, (_page, y, _x, text) in enumerate(method_lines):
            previous = method_lines[index - 1][3] if index else ""
            if index == 0 or previous[-1] in ".!?":
                for section_index, (section_y, _title) in enumerate(sections):
                    if section_index > current and y <= section_y + 12:
                        current = section_index
            assigned[current].append(text)
    chunks = []
    for section_index, (_y, title) in enumerate(sections):
        body = format_steps("\n".join(assigned[section_index]), "####")
        if body:
            chunks.append(f"### {title}\n\n{body}")
    assembly_lines = [row[3] for row in rows if row[0] != page and row[3].casefold() != "сборка десерта"]
    assembly = assembly_md(assembly_lines)
    if assembly:
        chunks.append(assembly)
    return add_notes("\n\n".join(chunks), [extra] if extra else [])


def render_recipe_lines(lines: list[str]) -> str:
    blocks: list[str] = []
    steps: list[str] = []
    bullets: list[str] = []
    quote = ""
    mode = ""

    def flush_steps() -> None:
        if steps:
            blocks.append("\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1)))
            steps.clear()

    def flush_bullets() -> None:
        if bullets:
            blocks.append("\n".join(f"- {item}" for item in bullets))
            bullets.clear()

    def flush_quote() -> None:
        nonlocal quote
        if quote:
            blocks.append(f"> {quote}")
            quote = ""

    for line in lines:
        if line.startswith("Хранение"):
            flush_steps()
            flush_bullets()
            quote = line
            mode = "quote"
            continue
        if re.match(r"^\d+\.\s", line):
            flush_quote()
            flush_bullets()
            steps.append(re.sub(r"^\d+\.\s*", "", line))
            mode = "step"
            continue
        if line[:1] in {"", "•", "·"}:
            flush_steps()
            flush_quote()
            bullets.append(line.lstrip("•· ").strip())
            mode = "bullet"
            continue
        if mode == "step" and steps and (line[:1].islower() or steps[-1][-1] not in ".!?"):
            steps[-1] = f"{steps[-1]} {line}"
            continue
        if mode == "quote" and line[:1].islower():
            quote = f"{quote} {line}"
            continue
        if mode == "bullet" and bullets and line[:1].islower():
            bullets[-1] = f"{bullets[-1]} {line}"
            continue
        flush_steps()
        flush_bullets()
        flush_quote()
        blocks.append(f"## {line}")
        mode = "heading"
    flush_steps()
    flush_bullets()
    flush_quote()
    return "\n\n".join(blocks)


def pdf_pastry_method(path: Path) -> str:
    texts = [text for _page, _y, _x, text in pdf_rows(path) if not text.startswith("Технологическая карта")]
    inventory = next(index for index, text in enumerate(texts) if text == "Инвентарь")
    composition = next(index for index, text in enumerate(texts) if text == "Состав" and index > inventory)
    step = next(index for index, text in enumerate(texts) if index > composition and re.match(r"^\d+\.", text))
    method_at = step - 1 if not re.match(r"^\d+\.", texts[step - 1]) else step
    notes = [
        text
        for text in texts[:inventory]
        if text.startswith("Расчёт") or text.startswith("Вес") or text.startswith("Ориентировочный")
    ]
    body = "## Инвентарь\n\n" + render_recipe_lines(texts[inventory + 1 : composition])
    body += "\n\n" + render_recipe_lines(texts[method_at:])
    return add_notes(body, notes)


def assembly_md(lines: list[str]) -> str:
    blocks: list[str] = []
    bullets: list[str] = []
    prose: list[str] = []

    def flush_bullets() -> None:
        if bullets:
            blocks.append("\n".join(f"- {item}" for item in bullets))
            bullets.clear()

    def flush_prose() -> None:
        if prose:
            formatted = format_steps("\n".join(prose), "###")
            if formatted:
                blocks.append(formatted)
            prose.clear()

    for line in lines:
        if line[:1] in {"*", "", "•"} or (bullets and line[:1].islower()):
            flush_prose()
            if line[:1] in {"*", "", "•"}:
                bullets.append(line.lstrip("*• ").strip())
            else:
                bullets[-1] = f"{bullets[-1]} {line}"
            continue
        flush_bullets()
        prose.append(line)
    flush_bullets()
    flush_prose()
    if not blocks:
        return ""
    return "## Сборка\n\n" + "\n\n".join(blocks)


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


def cake_method(diameter: str, bag: str, bento: bool) -> str:
    if bento:
        layers = (
            "2 коржа, 1 слой крема с начинкой. Снизу вверх:\n\n"
            "1. Нижний корж\n"
            "2. Крем\n"
            "3. Начинка\n"
            "4. Верхний корж\n\n"
            "Покрыть черновым слоем крема и отправить в морозилку на 10–15 минут."
        )
        repeat = "Положить следующий корж и повторить пункты 4–5 один раз."
        finish = "Черновое покрытие и в морозилку на 10–15 минут."
    else:
        layers = (
            "3 коржа, 2 слоя крема с начинкой. Снизу вверх:\n\n"
            "1. Нижний корж\n"
            "2. Крем, 1 слой\n"
            "3. Начинка, 1 слой\n"
            "4. Средний корж\n"
            "5. Крем, 2 слой\n"
            "6. Начинка, 2 слой\n"
            "7. Верхний корж\n\n"
            "Затянуть ацетатной пленкой и поставить под пресс."
        )
        repeat = "Положить следующий корж и повторить пункты 4–5 два раза."
        finish = "Ацетатная пленка и под пресс."
    return f"""## Бисквит

Диаметр примерно {diameter}. Размер может меняться по запросу заказчика или по просьбе шеф-кондитера или старшего кондитера.

## Слои

{layers}

## Крем

Крем чиз President. В составе крем на весь торт: внутрь и наружу. Один мешок на внутренние слои: {bag}.

## Правила сборки

1. Бисквит на дефрост. Можно использовать микроволновку на режиме разморозки.
2. Разрезать бисквит на коржи толщиной примерно 1 см.
3. Выложить нижний корж на подложку.
4. Тонко выдавить крем и размазать по бисквиту. Сделать бортик, кремовое кольцо, по краю.
5. Выложить начинку внутрь бортика.
6. {repeat}
7. {finish}

## Важно

- Соблюдать чистоту и аккуратность сборки.
- Вес торта указан ориентировочно, это готовый торт.
- Все ингредиенты указаны в граммах.

## Чек-лист перед отдачей

- Вес соответствует заказу
- Ровное и аккуратное покрытие
- Надежная подложка
- Чистая коробка
- Маркировка: вес, начинка, дата
- Фото готового торта
"""


def cake_cards(images: list[str]) -> tuple[list[dict], list[dict], list[dict]]:
    vanilla = {
        "0.6": "360",
        "1": "500",
        "1.5": "1000",
        "2": "1320",
        "2.5": "1650",
    }
    chocolate = {
        "0.6": "330",
        "1": "450",
        "1.5": "900",
        "2": "1200",
        "2.5": "1500",
    }
    biscuit_portions = {
        "Ванильный бисквит": vanilla,
        "Тропический бисквит": vanilla,
        "Шоколадный бисквит": chocolate,
        "Фисташковый бисквит": chocolate,
    }
    sizes = [
        ("Торт бенто 600 г", "0.6", "12 см", "174 г", True, "240", "70", "50"),
        ("Торт бенто 1 кг", "1", "16 см", "240 г", True, "320", "94", "66"),
        ("Торт 1,5 кг", "1.5", "16–18 см", "470 г", False, "600", "180", "160"),
        ("Торт 2 кг", "2", "18 см", "625 г", False, "800", "240", "210"),
        ("Торт 2,5 кг", "2.5", "18 см", "755 г", False, "1000", "270", "240"),
        ("Торт 3 кг", "3", "18 см", "906 г", False, "1200", "324", "288"),
    ]
    group = {
        "name": "Бисквит",
        "selection_type": "single",
        "is_required": True,
        "position": 0,
        "modifiers": [{"name": biscuit, "semi_product": biscuit} for biscuit in biscuit_portions],
    }
    cards = []
    links = []
    for name, basis, diameter, bag, bento, cream, butter, sugar in sizes:
        biscuits = [
            (biscuit, portions[basis])
            for biscuit, portions in biscuit_portions.items()
            if basis in portions
        ]
        lines = [
            component_line("Кремчиз", Decimal(cream), "g"),
            component_line("Масло сливочное", Decimal(butter), "g"),
            component_line("Сахарная пудра", Decimal(sugar), "g"),
        ]
        links.append(
            {
                "tech_card": name,
                "group": group["name"],
                "position": 0,
                "lines": [
                    {"modifier": biscuit, **semi_line(biscuit, Decimal(quantity)), "scales_by_weight": True}
                    for biscuit, quantity in biscuits
                ],
            }
        )
        cards.append(
            {
                "name": name,
                "kind": "weighted",
                "basis_weight_kg": basis,
                "basis_quantity": None,
                "category": "Торты",
                "method": cake_method(diameter, bag, bento).strip(),
                "images": images,
                "lines": without_unit(lines),
                "sections": [],
            }
        )
    return cards, [group], links


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
            ungrouped, sections, method, _yield = rows_to_parts(rows)
            title_key = filename.name
            cards.append(
                milk_girl(
                    title_key,
                    ungrouped,
                    sections,
                    method,
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
        if filename.suffix == ".docx":
            cards.append(docx_pastry_card(title, filename))
        else:
            cards.append(pdf_pastry_card(title, filename))
    pdfs = {nfc(path.name): path for path in SOURCE.glob("*.pdf")}
    jars = {
        "Дубай.pdf": (
            "Дубай",
            [
                (
                    "Брауни",
                    [
                        ("Масло сливочное", Decimal("150")),
                        ("Сахар", Decimal("80")),
                        ("Сахар тростниковый", Decimal("90")),
                        ("Яйцо", Decimal("135")),
                        ("Мука пшеничная", Decimal("70")),
                        ("Соль", Decimal("2")),
                        ("Молочный шоколад", Decimal("120")),
                    ],
                ),
                (
                    "Шоколадный мусс",
                    [
                        ("Молочный шоколад", Decimal("150")),
                        ("Сливки 33%", Decimal("80")),
                        ("Сливки 33%", Decimal("300")),
                        ("Желатин", Decimal("4")),
                        ("Вода", Decimal("20")),
                    ],
                ),
                (
                    "Ганаш на молочном шоколаде",
                    [
                        ("Молочный шоколад", Decimal("200")),
                        ("Сливки 33%", Decimal("200")),
                        ("Желатин", Decimal("4")),
                        ("Вода", Decimal("20")),
                    ],
                ),
                (
                    "Начинка Фисташка",
                    [
                        ("Катаифи", Decimal("225")),
                        ("Масло растительное", Decimal("30")),
                        ("Белый шоколад", Decimal("100")),
                        ("Фисташковая паста", Decimal("200")),
                    ],
                ),
            ],
            "Желатин замочен водой 1:5.",
        ),
        "Твикс.pdf": (
            "Твикс",
            [
                (
                    "Ванильное сабле",
                    [
                        ("Мука пшеничная", Decimal("280")),
                        ("Масло сливочное", Decimal("180")),
                        ("Миндальная мука", Decimal("52")),
                        ("Сахар", Decimal("110")),
                        ("Соль", Decimal("7")),
                        ("Ванильный экстракт", Decimal("10")),
                        ("Яйцо", Decimal("50")),
                        ("Молочный шоколад", Decimal("250")),
                    ],
                ),
                (
                    "Соленая карамель",
                    [
                        ("Сахар", Decimal("120")),
                        ("Масло сливочное", Decimal("40")),
                        ("Сливки 33%", Decimal("150")),
                        ("Соль", Decimal("1")),
                    ],
                ),
                (
                    "Шоколадный мусс",
                    [
                        ("Шоколад", Decimal("225")),
                        ("Сливки 33%", Decimal("120")),
                        ("Сливки 33%", Decimal("450")),
                        ("Желатин", Decimal("6")),
                        ("Вода", Decimal("30")),
                    ],
                ),
                (
                    "Ганаш на молочном шоколаде",
                    [
                        ("Шоколад", Decimal("200")),
                        ("Сливки 33%", Decimal("200")),
                        ("Желатин", Decimal("2")),
                        ("Вода", Decimal("10")),
                    ],
                ),
            ],
            "Яйцо в сабле: 1 шт = 50 г на всю партию. Желатин замочен водой 1:5.",
        ),
        "Медовик с облепихой.pdf": (
            "Медовик с облепихой",
            [
                (
                    "Корж",
                    [
                        ("Масло сливочное", Decimal("50")),
                        ("Сахар", Decimal("110")),
                        ("Мёд", Decimal("75")),
                        ("Сода", Decimal("9")),
                        ("Соль", Decimal("1")),
                        ("Мука пшеничная", Decimal("310")),
                        ("Яйцо", Decimal("85")),
                        ("Сок лимона", Decimal("12")),
                    ],
                ),
                (
                    "Сметанный крем",
                    [
                        ("Сметана 30%", Decimal("320")),
                        ("Сливки 33%", Decimal("100")),
                        ("Маскарпоне", Decimal("176")),
                        ("Мёд", Decimal("50")),
                        ("Сахарная пудра", Decimal("50")),
                    ],
                ),
                (
                    "Конфи облепиха",
                    [
                        ("Пюре облепихи", Decimal("360")),
                        ("Сахар", Decimal("120")),
                        ("Пектин NH", Decimal("12")),
                        ("Желатин", Decimal("5")),
                        ("Вода", Decimal("25")),
                    ],
                ),
            ],
            "Сметана в карточке указана как 25–30%. Желатин замочен водой 1:5.",
        ),
        "Морковный кекс.pdf": (
            "Морковный кекс",
            [
                (
                    "Морковный бисквит",
                    [
                        ("Морковь", Decimal("125")),
                        ("Пекан", Decimal("30")),
                        ("Изюм", Decimal("30")),
                        ("Мука пшеничная", Decimal("105")),
                        ("Разрыхлитель", Decimal("4")),
                        ("Сода", Decimal("2.5")),
                        ("Корица", Decimal("4")),
                        ("Соль", Decimal("3")),
                        ("Сахар", Decimal("125")),
                        ("Сахар тростниковый", Decimal("40")),
                        ("Масло растительное", Decimal("135")),
                        ("Яйцо", Decimal("125")),
                    ],
                ),
                (
                    "Сырный крем",
                    [
                        ("Сливки 33%", Decimal("450")),
                        ("Сахарная пудра", Decimal("60")),
                        ("Кремчиз", Decimal("250")),
                        ("Маскарпоне", Decimal("100")),
                        ("Корица", Decimal("2")),
                    ],
                ),
            ],
            "",
        ),
        "Фундучное наслаждение.pdf": (
            "Фундучное наслаждение",
            [
                (
                    "Дакуаз фундучный",
                    [
                        ("Яичный белок", Decimal("75")),
                        ("Сахар", Decimal("25")),
                        ("Сахарная пудра", Decimal("60")),
                        ("Миндальная мука", Decimal("60")),
                        ("Фундучное пралине", Decimal("15")),
                    ],
                ),
                (
                    "Соленая карамель",
                    [
                        ("Сахар", Decimal("120")),
                        ("Сливки 33%", Decimal("150")),
                        ("Масло сливочное", Decimal("40")),
                        ("Соль", Decimal("1")),
                    ],
                ),
                (
                    "Пралине мусс",
                    [
                        {"semi_product": "Заварной крем для банок", "quantity": "250"},
                        ("Фундучное пралине", Decimal("100")),
                        ("Сливки 33%", Decimal("600")),
                        ("Желатин", Decimal("5")),
                        ("Вода", Decimal("25")),
                    ],
                ),
                (
                    "Ганаш на молочном шоколаде",
                    [
                        ("Молочный шоколад", Decimal("100")),
                        ("Сливки 33%", Decimal("100")),
                    ],
                ),
            ],
            "Заварной крем вынесен в полуфабрикат и в мусс входит строкой 250 г на партию. Желатин замочен водой 1:5.",
        ),
        "Эксзотический десерт.pdf": (
            "Экзотический десерт",
            [
                (
                    "Бисквит Дакуаз Кокос",
                    [
                        ("Сахарная пудра", Decimal("125")),
                        ("Миндальная мука", Decimal("25")),
                        ("Кокосовая стружка", Decimal("125")),
                        ("Яичный белок", Decimal("150")),
                        ("Сахар", Decimal("50")),
                    ],
                ),
                (
                    "Желе манго-маракуйя",
                    [
                        ("Пюре манго", Decimal("360")),
                        ("Пюре маракуйи", Decimal("90")),
                        ("Сахар", Decimal("90")),
                        ("Желатин", Decimal("9")),
                        ("Вода", Decimal("45")),
                    ],
                ),
                (
                    "Крем кокос",
                    [
                        {"semi_product": "Заварной крем для банок", "quantity": "250"},
                        ("Пюре кокоса", Decimal("250")),
                        ("Сливки 33%", Decimal("250")),
                    ],
                ),
            ],
            "Заварной крем вынесен в полуфабрикат и в кокосовый крем входит строкой 250 г на партию. "
            "Желатин желе замочен водой 1:5. Конфи в сборке — это желе манго-маракуйя.",
        ),
    }
    semis.append(custard_jar())
    for filename, (title, grouped, extra) in jars.items():
        path = pdfs[nfc(filename)]
        cards.append(jar_card(title, grouped, culinart_method(path, extra)))
    sheet = IMAGES / "kremchiz-sheet.png"
    shutil.copy(SOURCE / "b0ce358c-c22e-4e69-9866-7e45530f1149.png", sheet)
    cakes, modifier_groups, tech_card_modifiers = cake_cards(["images/kremchiz-sheet.png"])
    cards.extend(cakes)
    ingredients: dict[str, str] = {}
    for collection in (semis, cards):
        for entity in collection:
            rows = list(entity["lines"])
            if "sections" in entity:
                for section in entity["sections"]:
                    rows.extend(section["lines"])
            for row in rows:
                if "ingredient" not in row:
                    continue
                unit = "g"
                ingredients.setdefault(row["ingredient"], unit)
    for card in cards:
        rows = list(card["lines"])
        for section in card["sections"]:
            rows.extend(section["lines"])
        for row in rows:
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
        "modifier_groups": modifier_groups,
        "tech_card_modifiers": tech_card_modifiers,
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
        pieces = entity["basis_quantity"] if entity["basis_quantity"] is not None else "-"
        print(f"CARD {entity['kind']} {basis} pcs {pieces} {entity['name']} lines {len(entity['lines'])}")


if __name__ == "__main__":
    build()
