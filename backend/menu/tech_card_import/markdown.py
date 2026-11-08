from dataclasses import dataclass


@dataclass(frozen=True)
class TextBlock:
    text: str


@dataclass(frozen=True)
class TableBlock:
    rows: list[list[str]]


def markdown_cell(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def render_table(rows: list[list[str]]) -> str:
    if not rows:
        raise ValueError("Table has no rows")
    width = len(rows[0])
    if width == 0:
        raise ValueError("Table has no columns")
    for row in rows:
        if len(row) != width:
            raise ValueError("Table rows have different widths")

    def line(row: list[str]) -> str:
        return "| " + " | ".join(markdown_cell(cell) for cell in row) + " |"

    separator = "| " + " | ".join("---" for _ in range(width)) + " |"
    return "\n".join([line(rows[0]), separator, *[line(row) for row in rows[1:]]])


def render_markdown(blocks: list[TextBlock | TableBlock]) -> str:
    parts: list[str] = []
    for block in blocks:
        if isinstance(block, TextBlock):
            parts.append(block.text)
        else:
            parts.append(render_table(block.rows))
    return "\n\n".join(parts)
