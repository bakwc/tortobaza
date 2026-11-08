import zipfile
from io import BytesIO
from xml.etree import ElementTree

from menu.tech_card_import.markdown import TableBlock, TextBlock

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def paragraph_text(paragraph: ElementTree.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == f"{W}t" and node.text:
            parts.append(node.text)
        elif node.tag == f"{W}tab":
            parts.append("\t")
        elif node.tag == f"{W}br":
            parts.append("\n")
    return "".join(parts).strip()


def cell_parts(cell: ElementTree.Element) -> tuple[str, int, str | None]:
    if any(node.tag == f"{W}tbl" for node in cell.iter()):
        raise ValueError("Nested tables are not supported")
    props = cell.find(f"{W}tcPr")
    span = 1
    merge = None
    if props is not None:
        grid_span = props.find(f"{W}gridSpan")
        if grid_span is not None:
            span = int(grid_span.get(f"{W}val"))
        vertical = props.find(f"{W}vMerge")
        if vertical is not None:
            merge = "restart" if vertical.get(f"{W}val") == "restart" else "continue"
    if span < 1:
        raise ValueError("Table cell span is empty")
    lines = [text for paragraph in cell.findall(f"{W}p") if (text := paragraph_text(paragraph))]
    return "\n".join(lines), span, merge


def table_rows(table: ElementTree.Element) -> list[list[str]]:
    parsed = [[cell_parts(cell) for cell in row.findall(f"{W}tc")] for row in table.findall(f"{W}tr")]
    if not parsed:
        raise ValueError("Docx table has no rows")
    grid = table.find(f"{W}tblGrid")
    width = len(grid.findall(f"{W}gridCol")) if grid is not None else 0
    if width == 0:
        width = max(sum(span for _, span, _ in row) for row in parsed)
    rows: list[list[str]] = []
    for row in parsed:
        values = [""] * width
        column = 0
        for text, span, merge in row:
            if column + span > width:
                raise ValueError("Table cell extends past the grid")
            values[column] = "" if merge == "continue" else text
            column += span
        rows.append(values)
    return rows


def docx_blocks(data: bytes) -> list[TextBlock | TableBlock]:
    with zipfile.ZipFile(BytesIO(data)) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    body = root.find(f"{W}body")
    if body is None:
        raise ValueError("Docx document has no body")
    blocks: list[TextBlock | TableBlock] = []
    paragraphs: list[str] = []

    def flush() -> None:
        text = "\n".join(paragraphs).strip()
        paragraphs.clear()
        if text:
            blocks.append(TextBlock(text))

    for child in body:
        if child.tag == f"{W}p":
            text = paragraph_text(child)
            if text:
                paragraphs.append(text)
        elif child.tag == f"{W}tbl":
            flush()
            blocks.append(TableBlock(table_rows(child)))
        elif child.tag == f"{W}sectPr":
            continue
        else:
            raise ValueError(f"Unsupported docx block {child.tag}")
    flush()
    return blocks
