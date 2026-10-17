import json
import re
import zipfile
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree

import build_tech_cards_data as base

SOURCE = Path("/Users/fippo/Documents/tech-cards-2")
ROOT = Path(__file__).resolve().parents[1] / "backend" / "menu" / "data"
WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
YIELD_RE = re.compile(r"Выход:\s*(\d+)\s*шт", re.IGNORECASE)
TAG_RE = re.compile(r"^(.*?)\s*\(([^)]+)\)\s*$")
GELATIN_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*\+\s*(\d+(?:[.,]\d+)?)\s*гр\s+воды",
    re.IGNORECASE,
)
RANGE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*[–—-]\s*(\d+(?:[.,]\d+)?)")
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
STEP_RE = re.compile(r"(?<=\S)(?=\d+\.\s)")

NAME_MAP = {
    "кокосовое пюре": "Пюре кокоса",
    "желатин 220 бл": "Желатин",
    "сгущеное молоко": "Сгущённое молоко",
    "темный шоколад": "Тёмный шоколад",
    "шоколад темный": "Тёмный шоколад",
    "рубленный фундук": "Фундук",
    "фундучные половинки": "Фундук",
    "криспи шарики": "Криспи",
    "тесто катаифи": "Катаифи",
    "растительное масло рафинированное": "Масло растительное",
    "масло растительное рафинированное": "Масло растительное",
    "сливки 33": "Сливки 33%",
    "сливки 33 (1)": "Сливки 33%",
    "сливки 33 (2)": "Сливки 33%",
}

SEMI_NAMES = {
    "бисквит шоколадный": "Шоколадный бисквит",
    "шоколадный бисквит": "Шоколадный бисквит",
    "бисквит ванильный": "Ванильный бисквит",
    "ванильный бисквит": "Ванильный бисквит",
    "морковный бисквит": "Морковный бисквит",
    "бисквит кокосовый": "Кокосовый бисквит",
    "кокосовый бисквит": "Кокосовый бисквит",
    "медовые коржи": "Медовые коржи",
}

EXISTING_SEMIS = {"Шоколадный бисквит", "Ванильный бисквит", "Морковный бисквит"}
EMPTY_SEMIS = {"Кокосовый бисквит", "Медовые коржи"}

TAG_SECTIONS = {
    "ганаш": "Ганаш",
    "начинка": "Начинка",
    "глазурь": "Глазурь",
    "покрытие": "Покрытие",
    "декор": "Декор",
    "в замес": "Основа",
}

PAGES = (
    {
        "match": "баунти",
        "name": "Картошка Баунти",
        "base_sections": ("Ганаш кокосовый",),
        "ball": Decimal("70"),
        "pieces": 18,
        "drop": (),
        "notes": (),
    },
    {
        "match": "киндер",
        "name": "Картошка Киндер кантри",
        "base_sections": ("Картошечная масса",),
        "ball": Decimal("55"),
        "pieces": 22,
        "drop": (("Ганаш ванильный", "Ванильный бисквит"),),
        "notes": (
            "Ванильный бисквит 800 г в секции «Ганаш ванильный» не включён: "
            "тот же бисквит указан в «Картошечной массе».",
        ),
    },
    {
        "match": "ферреро",
        "name": "Картошка Ферреро",
        "base_sections": ("Ганаш шоколадный",),
        "ball": Decimal("55"),
        "pieces": 29,
        "drop": (),
        "notes": (),
    },
    {
        "match": "ваниль",
        "name": "Картошка классическая ванильная",
        "base_sections": ("Ганаш шоколадный",),
        "ball": Decimal("80"),
        "pieces": 16,
        "drop": (),
        "notes": (),
    },
    {
        "match": "копия",
        "name": "Картошка классическая в глазури",
        "base_sections": ("Ганаш шоколадный",),
        "ball": Decimal("80"),
        "pieces": 16,
        "drop": (),
        "notes": (),
    },
    {
        "match": "классическ",
        "name": "Картошка классическая",
        "base_sections": ("Ганаш шоколадный",),
        "ball": Decimal("80"),
        "pieces": 16,
        "drop": (),
        "notes": (),
    },
)

DOCX = (
    {
        "match": "dubai",
        "name": "Картошка Дубайская",
        "pieces": 20,
        "decor_names": (),
    },
    {
        "match": "medovik",
        "name": "Картошка Медовик",
        "pieces": 18,
        "decor_names": (),
    },
    {
        "match": "морков",
        "name": "Картошка морковная с курагой и черносливом",
        "pieces": 18,
        "decor_names": ("Грецкий орех",),
    },
)


def resolve_name(name: str) -> tuple[str, str]:
    key = name.strip().casefold()
    if key in SEMI_NAMES:
        return "semi_product", SEMI_NAMES[key]
    if key in NAME_MAP:
        return "ingredient", NAME_MAP[key]
    return "ingredient", base.canon(name.strip())


def ingredient_line(name: str, quantity: Decimal) -> dict:
    return {"ingredient": name, "quantity": base.qstr(quantity), "loss_percent": "0"}


def amount_lines(label: str, amount: str) -> tuple[list[dict], list[str]]:
    text = amount.strip()
    gelatin = GELATIN_RE.fullmatch(text)
    if gelatin:
        kind, value = resolve_name(label)
        if kind != "ingredient" or value != "Желатин":
            raise RuntimeError(f"gelatin row {label} / {text}")
        return [
            ingredient_line(value, base.dec(gelatin.group(1))),
            ingredient_line("Вода", base.dec(gelatin.group(2))),
        ], []
    ranged = RANGE_RE.fullmatch(text)
    if ranged:
        kind, value = resolve_name(label)
        if kind != "ingredient":
            raise RuntimeError(f"range row {label} / {text}")
        middle = (base.dec(ranged.group(1)) + base.dec(ranged.group(2))) / 2
        note = f"{value}: в карточке {text}, в составе {base.qstr(middle)} г"
        return [ingredient_line(value, middle)], [note]
    if NUMBER_RE.fullmatch(text) is None:
        raise RuntimeError(f"quantity {label} / {text}")
    kind, value = resolve_name(label)
    quantity = base.dec(text)
    if kind == "semi_product":
        return [base.semi_line(value, quantity)], []
    return [ingredient_line(value, quantity)], []


def pages_config(filename: str) -> dict:
    folded = base.nfc(Path(filename).stem).casefold()
    for config in PAGES:
        if config["match"] in folded:
            return config
    raise RuntimeError(f"unnamed pages file {filename}")


def section_mass(sections: list[dict], names: tuple[str, ...]) -> Decimal:
    total = Decimal("0")
    for name in names:
        matches = [section for section in sections if section["name"].casefold() == name.casefold()]
        if len(matches) != 1:
            raise RuntimeError(f"base section {name}")
        for line in matches[0]["lines"]:
            total += Decimal(line["quantity"])
    return total


def pages_card(path: Path) -> dict:
    config = pages_config(path.name)
    tables = base.pages_tables(path)
    rows = [row for table in tables for row in table]
    if not rows:
        raise RuntimeError(f"empty pages {path.name}")
    drop_pairs = set(config["drop"])
    dropped: list[tuple[str, str]] = []
    sections: list[dict] = []
    current: dict | None = None
    method_bits: list[str] = []
    notes: list[str] = list(config["notes"])
    for name, qty, method in rows:
        cleaned_method = method.strip()
        if cleaned_method and cleaned_method.casefold() != "метод приготовления":
            method_bits.append(cleaned_method)
        label = name.strip()
        amount = qty.strip()
        if label.casefold() in {"ингредиенты", "ингридиенты"}:
            continue
        if amount.casefold().startswith("кол-во"):
            continue
        if not amount:
            if not label:
                continue
            current = {"name": base.heading_title(label), "method": "", "lines": []}
            sections.append(current)
            continue
        if current is None:
            raise RuntimeError(f"ingredient before a section in {path.name}: {label}")
        parsed, parsed_notes = amount_lines(label, amount)
        notes.extend(parsed_notes)
        for line in parsed:
            semi_name = line.get("semi_product")
            if semi_name is not None and (current["name"], semi_name) in drop_pairs:
                if Decimal(line["quantity"]) != Decimal("800"):
                    raise RuntimeError(f"{config['name']}: dropped {semi_name} {line['quantity']}")
                dropped.append((current["name"], semi_name))
                continue
            current["lines"].append(line)
    for section_name, semi_name in config["drop"]:
        if dropped.count((section_name, semi_name)) != 1:
            raise RuntimeError(f"{config['name']}: drop {section_name} / {semi_name}")
    mass = section_mass(sections, config["base_sections"])
    count = int(mass // config["ball"])
    if count != config["pieces"]:
        raise RuntimeError(f"{config['name']}: {count} pcs from {mass} g")
    method = base.format_steps("\n\n".join(method_bits), "###")
    if not method.strip():
        raise RuntimeError(f"empty method {config['name']}")
    notes.append(
        f"Выход посчитан: масса основы {base.qstr(mass)} г / шарик {base.qstr(config['ball'])} г = {count} шт."
    )
    stored = [section for section in sections if section["lines"]]
    if not stored:
        raise RuntimeError(f"no lines in {config['name']}")
    return {
        "name": config["name"],
        "kind": "piece",
        "basis_weight_kg": None,
        "basis_quantity": count,
        "category": "Пирожные",
        "method": base.add_notes(method, notes).strip(),
        "images": [],
        "lines": [],
        "sections": base.card_sections(stored),
    }


def docx_config(filename: str) -> dict:
    folded = base.nfc(filename).casefold()
    for config in DOCX:
        if config["match"] in folded:
            return config
    raise RuntimeError(f"unnamed docx file {filename}")


def docx_items(path: Path) -> list[tuple[str, str | list[list[str]]]]:
    archive = zipfile.ZipFile(path)
    root = ElementTree.fromstring(archive.read("word/document.xml"))
    body = root.find(f"{WORD}body")
    items: list[tuple[str, str | list[list[str]]]] = []
    for element in list(body):
        tag = element.tag.replace(WORD, "")
        if tag == "tbl":
            rows = []
            for row in element.findall(f"{WORD}tr"):
                rows.append([base.docx_runs(cell, WORD) for cell in row.findall(f"{WORD}tc")])
            items.append(("tbl", rows))
            continue
        if tag != "p":
            continue
        text = base.docx_runs(element, WORD)
        if text:
            items.append(("p", text))
    return items


def split_tag(label: str, decor_names: tuple[str, ...]) -> tuple[str, str]:
    match = TAG_RE.match(label.strip())
    if match:
        tag = match.group(2).strip().casefold()
        if tag not in TAG_SECTIONS:
            raise RuntimeError(f"unknown tag {label}")
        return match.group(1).strip(), TAG_SECTIONS[tag]
    if label.strip() in decor_names:
        return label.strip(), "Декор"
    return label.strip(), "Основа"


def assembly_md(text: str) -> tuple[str, list[str]]:
    body, marker, tail = text.partition("Важно:")
    notes = [f"Важно: {tail.strip()}"] if marker else []
    parts = [part.strip() for part in STEP_RE.split(body.strip()) if part.strip()]
    steps = [re.sub(r"^\d+\.\s*", "", part).strip() for part in parts]
    if len(steps) > 1:
        rendered = "\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1))
    else:
        rendered = body.strip()
    if not rendered:
        raise RuntimeError("empty assembly")
    return f"## Сборка\n\n{rendered}", notes


def docx_card(path: Path) -> dict:
    config = docx_config(path.name)
    items = docx_items(path)
    tables = [value for kind, value in items if kind == "tbl"]
    if len(tables) != 1:
        raise RuntimeError(f"{path.name}: tables {len(tables)}")
    counts = []
    for kind, value in items:
        if kind != "p":
            continue
        found = YIELD_RE.search(value)
        if found:
            counts.append(int(found.group(1)))
    if counts != [config["pieces"]]:
        raise RuntimeError(f"{config['name']}: yield {counts}")
    assembly_parts: list[str] = []
    started = False
    for kind, value in items:
        if kind == "p" and value.casefold() == "сборка":
            started = True
            continue
        if started and kind == "p":
            assembly_parts.append(value)
    if not started or not assembly_parts:
        raise RuntimeError(f"no assembly in {config['name']}")
    assembly, assembly_notes = assembly_md("\n\n".join(assembly_parts))
    grouped: dict[str, dict] = {}
    notes = list(assembly_notes)
    for cells in tables[0]:
        if len(cells) < 2:
            raise RuntimeError(f"{config['name']}: short row {cells}")
        label = cells[0].strip()
        amount = cells[1].strip()
        method = cells[2].strip() if len(cells) > 2 else ""
        if not label or label.casefold() == "ингредиент":
            continue
        if label.casefold() == "итого":
            text = label
            if amount:
                text = f"{text}: {amount}"
            if method:
                text = f"{text}. {method}"
            notes.append(text)
            continue
        if NUMBER_RE.fullmatch(amount) is None:
            raise RuntimeError(f"{config['name']}: quantity {label} / {amount}")
        raw_name, section_name = split_tag(label, config["decor_names"])
        kind, value = resolve_name(raw_name)
        quantity = base.dec(amount)
        if kind == "semi_product":
            line = base.semi_line(value, quantity)
        else:
            line = ingredient_line(value, quantity)
        section = grouped.get(section_name)
        if section is None:
            section = {"name": section_name, "methods": [], "lines": []}
            grouped[section_name] = section
        section["lines"].append(line)
        if method:
            section["methods"].append(method)
    sections = []
    for section in grouped.values():
        body = "\n\n".join(section["methods"])
        sections.append(
            {
                "name": section["name"],
                "method": base.format_steps(body, "####") if body else "",
                "lines": section["lines"],
            }
        )
    if not sections:
        raise RuntimeError(f"no lines in {config['name']}")
    return {
        "name": config["name"],
        "kind": "piece",
        "basis_weight_kg": None,
        "basis_quantity": config["pieces"],
        "category": "Пирожные",
        "method": base.add_notes(assembly, notes).strip(),
        "images": [],
        "lines": [],
        "sections": base.card_sections(sections),
    }


def referenced_semis(cards: list[dict]) -> set[str]:
    found = set()
    for card in cards:
        for section in card["sections"]:
            for line in section["lines"]:
                semi_name = line.get("semi_product")
                if semi_name is not None:
                    found.add(semi_name)
        for line in card["lines"]:
            semi_name = line.get("semi_product")
            if semi_name is not None:
                found.add(semi_name)
    return found


def empty_semi(name: str) -> dict:
    return {
        "name": name,
        "unit": "g",
        "yield_quantity": "1000",
        "method": "Рецепт не заведён",
        "images": [],
        "lines": [],
    }


def build() -> None:
    cards: list[dict] = []
    for path in sorted(SOURCE.iterdir()):
        if path.name == ".DS_Store":
            continue
        if path.suffix == ".pages":
            cards.append(pages_card(path))
            continue
        if path.suffix == ".docx":
            cards.append(docx_card(path))
            continue
        raise RuntimeError(f"unexpected file {path.name}")
    if len(cards) != 9:
        raise RuntimeError(f"cards {len(cards)}")
    found = referenced_semis(cards)
    if found != EXISTING_SEMIS | EMPTY_SEMIS:
        raise RuntimeError(f"semis {sorted(found)}")
    semis = [empty_semi(name) for name in sorted(EMPTY_SEMIS)]
    ingredients: dict[str, str] = {}
    for card in cards:
        rows = list(card["lines"])
        for section in card["sections"]:
            rows.extend(section["lines"])
        for row in rows:
            if "ingredient" in row:
                ingredients.setdefault(row["ingredient"], "g")
    payload = {
        "categories": [{"name": "Пирожные", "position": 1}],
        "ingredients": [{"name": name, "unit": unit} for name, unit in sorted(ingredients.items())],
        "semi_products": semis,
        "tech_cards": cards,
        "modifier_groups": [],
        "tech_card_modifiers": [],
        "existing_semi_products": sorted(EXISTING_SEMIS),
    }
    names = [row["name"] for row in semis + cards]
    if len(names) != len(set(names)):
        raise RuntimeError(f"duplicate names {[name for name in names if names.count(name) > 1]}")
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "tech_cards_2.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"semis {len(semis)} cards {len(cards)} ingredients {len(ingredients)}")
    for entity in semis:
        print(f"SEMI {entity['name']} yield {entity['yield_quantity']} lines {len(entity['lines'])}")
    for entity in cards:
        print(f"CARD {entity['kind']} pcs {entity['basis_quantity']} {entity['name']} sections {len(entity['sections'])}")


if __name__ == "__main__":
    build()
