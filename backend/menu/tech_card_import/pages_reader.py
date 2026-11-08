import zipfile
from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO
from struct import unpack

from numbers_parser.cell import _unpack_decimal128
from numbers_parser.constants import COLON_TRACT_NODE
from numbers_parser.generated import TSTArchives_pb2 as TST
from numbers_parser.generated.mapping import ID_NAME_MAP
from numbers_parser.generated.TSTArchives_pb2 import (
    MergeRegionMapArchive,
    RichTextPayloadArchive,
    TableDataList,
    TableInfoArchive,
    TableModelArchive,
    Tile,
)
from numbers_parser.generated.TSWPArchives_pb2 import DrawableAttachmentArchive, StorageArchive
from numbers_parser.model import get_storage_buffers_for_row

from menu.tech_card_import.iwa import iter_objects
from menu.tech_card_import.markdown import TableBlock, TextBlock

STORAGE = 2001
DRAWABLE_ATTACHMENT = 2003
IMAGE = 3005
TABLE_INFO = 6000
TABLE_MODEL = 6001
TILE = 6002
TABLE_DATA_LIST = 6005
MERGE_REGION_MAP = 6144
RICH_TEXT_PAYLOAD = 6218
OBJECT_REPLACEMENT = "\ufffc"


@dataclass(frozen=True)
class PagesDocument:
    blocks: list[TextBlock | TableBlock]
    preview: bytes


def normalize_text(value: str) -> str:
    return value.replace("\u2028", "\n").replace("\u2029", "\n").replace("\r\n", "\n").replace("\r", "\n")


def number_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def read_objects(archive: zipfile.ZipFile) -> dict[int, dict[int, list[bytes]]]:
    objects: dict[int, dict[int, list[bytes]]] = {}
    for name in archive.namelist():
        if not name.endswith(".iwa"):
            continue
        for identifier, message_type, payload in iter_objects(archive.read(name)):
            bucket = objects.setdefault(identifier, {})
            payloads = bucket.setdefault(message_type, [])
            if payload not in payloads:
                payloads.append(payload)
    return objects


def decode(objects: dict[int, dict[int, list[bytes]]], identifier: int, message_type: int):
    payloads = objects[identifier]
    if message_type not in payloads:
        found = [ID_NAME_MAP[kind].DESCRIPTOR.full_name for kind in payloads if kind in ID_NAME_MAP]
        raise ValueError(f"Object {identifier} has no message {message_type}, found {found}")
    stored = payloads[message_type]
    if len(stored) != 1:
        raise ValueError(f"Conflicting IWA object {identifier} type {message_type}")
    message = ID_NAME_MAP[message_type]()
    message.ParseFromString(stored[0])
    return message


def data_list(objects: dict[int, dict[int, list[bytes]]], identifier: int) -> TableDataList:
    if identifier == 0:
        return TableDataList()
    listing = decode(objects, identifier, TABLE_DATA_LIST)
    if listing.segments:
        raise ValueError("Segmented table data is not supported")
    return listing


def string_map(listing: TableDataList) -> dict[int, str]:
    return {entry.key: entry.string for entry in listing.entries}


def rich_map(objects: dict[int, dict[int, list[bytes]]], listing: TableDataList) -> dict[int, str]:
    texts: dict[int, str] = {}
    for entry in listing.entries:
        payload_id = entry.rich_text_payload.identifier
        if payload_id == 0:
            raise ValueError(f"Rich text entry {entry.key} has no payload")
        payload = decode(objects, payload_id, RICH_TEXT_PAYLOAD)
        if not isinstance(payload, RichTextPayloadArchive):
            raise ValueError("Rich text payload has the wrong type")
        storage = decode(objects, payload.storage.identifier, STORAGE)
        if not isinstance(storage, StorageArchive):
            raise ValueError("Rich text storage has the wrong type")
        if storage.table_attachment.entries:
            raise ValueError("Attachment inside a table cell")
        texts[entry.key] = normalize_text("".join(storage.text)).strip()
    return texts


def range_end(archive) -> int:
    if archive.HasField("range_end"):
        return archive.range_end
    return archive.range_begin


def formula_ranges(formulas) -> list[tuple[int, int, int, int]]:
    ranges: list[tuple[int, int, int, int]] = []
    for formula in formulas:
        nodes = formula.formula.AST_node_array.AST_node
        if len(nodes) == 0 or nodes[0].AST_node_type != COLON_TRACT_NODE:
            raise ValueError("Merge formula is not a cell range")
        rows = nodes[0].AST_colon_tract.absolute_row
        columns = nodes[0].AST_colon_tract.absolute_column
        if len(rows) != 1 or len(columns) != 1:
            raise ValueError("Merge formula is not a single range")
        ranges.append((rows[0].range_begin, range_end(rows[0]), columns[0].range_begin, range_end(columns[0])))
    return ranges


def region_ranges(region_map: MergeRegionMapArchive) -> list[tuple[int, int, int, int]]:
    ranges: list[tuple[int, int, int, int]] = []
    for cell_range in region_map.cell_range:
        column = cell_range.origin.packedData >> 16
        row = cell_range.origin.packedData & 0xFFFF
        columns = cell_range.size.packedData >> 16
        rows = cell_range.size.packedData & 0xFFFF
        ranges.append((row, row + rows - 1, column, column + columns - 1))
    return ranges


def merge_ranges(objects: dict[int, dict[int, list[bytes]]], model: TableModelArchive) -> list[tuple[int, int, int, int]]:
    formulas = model.merge_owner.formula_store.formulas
    if len(formulas) > 0:
        return formula_ranges(formulas)
    identifier = model.base_data_store.merge_region_map.identifier
    if identifier == 0:
        return []
    region_map = decode(objects, identifier, MERGE_REGION_MAP)
    if not isinstance(region_map, MergeRegionMapArchive):
        raise ValueError("Merge map has the wrong type")
    return region_ranges(region_map)


def cell_text(buffer: bytes | None, strings: dict[int, str], rich: dict[int, str]) -> str:
    if not buffer:
        return ""
    if buffer[0] != 5:
        raise ValueError(f"Cell storage version {buffer[0]} is unsupported")
    cell_type = buffer[1]
    flags = unpack("<i", buffer[8:12])[0]
    offset = 12
    number = None
    string_id = None
    rich_id = None
    if flags & 0x1:
        number = _unpack_decimal128(buffer[offset : offset + 16])
        offset += 16
    if flags & 0x2:
        offset += 8
    if flags & 0x4:
        offset += 8
    if flags & 0x8:
        string_id = unpack("<i", buffer[offset : offset + 4])[0]
        offset += 4
    if flags & 0x10:
        rich_id = unpack("<i", buffer[offset : offset + 4])[0]
    if cell_type == TST.numberCellType:
        if number is None:
            raise ValueError("Number cell has no value")
        return number_text(number)
    if cell_type == TST.textCellType:
        if string_id not in strings:
            raise ValueError(f"Missing string {string_id}")
        return normalize_text(strings[string_id]).strip()
    if cell_type == TST.automaticCellType:
        if rich_id not in rich:
            raise ValueError(f"Missing rich text {rich_id}")
        return rich[rich_id]
    if cell_type in (TST.genericCellType, TST.spanCellType):
        return ""
    raise ValueError(f"Cell type {cell_type} is unsupported")


def covered_cells(ranges: list[tuple[int, int, int, int]], row_count: int, column_count: int) -> dict[tuple[int, int], tuple[int, int]]:
    covered: dict[tuple[int, int], tuple[int, int]] = {}
    for row_start, row_end, column_start, column_end in ranges:
        if row_start > row_end or column_start > column_end:
            raise ValueError("Merge range is reversed")
        if row_start < 0 or column_start < 0 or row_end >= row_count or column_end >= column_count:
            raise ValueError("Merge range is outside the table")
        for row in range(row_start, row_end + 1):
            for column in range(column_start, column_end + 1):
                if (row, column) in covered:
                    raise ValueError("Overlapping merges")
                covered[(row, column)] = (row_start, column_start)
    return covered


def table_block(objects: dict[int, dict[int, list[bytes]]], info: TableInfoArchive) -> TableBlock:
    model = decode(objects, info.tableModel.identifier, TABLE_MODEL)
    if not isinstance(model, TableModelArchive):
        raise ValueError("Table model has the wrong type")
    row_count = model.number_of_rows
    column_count = model.number_of_columns
    if row_count == 0 or column_count == 0:
        raise ValueError("Table has no cells")
    tiles = list(model.base_data_store.tiles.tiles)
    if len(tiles) != 1:
        raise ValueError(f"Table has {len(tiles)} tiles")
    tile = decode(objects, tiles[0].tile.identifier, TILE)
    if not isinstance(tile, Tile):
        raise ValueError("Tile has the wrong type")
    strings = string_map(data_list(objects, model.base_data_store.stringTable.identifier))
    rich = rich_map(objects, data_list(objects, model.base_data_store.rich_text_table.identifier))
    rows_by_index: dict[int, object] = {}
    for info_row in tile.rowInfos:
        if info_row.tile_row_index in rows_by_index:
            raise ValueError(f"Duplicate table row {info_row.tile_row_index}")
        rows_by_index[info_row.tile_row_index] = info_row
    if any(index < 0 or index >= row_count for index in rows_by_index):
        raise ValueError("Table row is outside the model")
    covered = covered_cells(merge_ranges(objects, model), row_count, column_count)
    rows: list[list[str]] = []
    for row_index in range(row_count):
        info_row = rows_by_index.get(row_index)
        buffers = []
        if info_row is not None and info_row.cell_storage_buffer:
            buffers = get_storage_buffers_for_row(
                info_row.cell_storage_buffer,
                info_row.cell_offsets,
                column_count,
                info_row.has_wide_offsets,
            )
        values: list[str] = []
        for column_index in range(column_count):
            origin = covered.get((row_index, column_index))
            if origin is not None and origin != (row_index, column_index):
                values.append("")
                continue
            buffer = buffers[column_index] if column_index < len(buffers) else None
            values.append(cell_text(buffer, strings, rich))
        rows.append(values)
    return TableBlock(rows)


def body_storage(objects: dict[int, dict[int, list[bytes]]]) -> StorageArchive:
    found: list[StorageArchive] = []
    for payloads in objects.values():
        if STORAGE not in payloads:
            continue
        stored = payloads[STORAGE]
        if len(stored) != 1:
            raise ValueError("Conflicting body storage")
        storage = StorageArchive()
        storage.ParseFromString(stored[0])
        if storage.kind == 0 and storage.table_attachment.entries:
            found.append(storage)
    if len(found) != 1:
        raise ValueError(f"Pages file has {len(found)} body texts")
    return found[0]


def attachment_block(objects: dict[int, dict[int, list[bytes]]], identifier: int) -> TableBlock | None:
    attachment = decode(objects, identifier, DRAWABLE_ATTACHMENT)
    if not isinstance(attachment, DrawableAttachmentArchive):
        raise ValueError("Attachment has the wrong type")
    payloads = objects[attachment.drawable.identifier]
    if TABLE_INFO in payloads:
        info = decode(objects, attachment.drawable.identifier, TABLE_INFO)
        if not isinstance(info, TableInfoArchive):
            raise ValueError("Table info has the wrong type")
        return table_block(objects, info)
    if IMAGE in payloads:
        return None
    names = [ID_NAME_MAP[kind].DESCRIPTOR.full_name for kind in payloads if kind in ID_NAME_MAP]
    raise ValueError(f"Unsupported attachment {names}")


def document_blocks(objects: dict[int, dict[int, list[bytes]]], storage: StorageArchive) -> list[TextBlock | TableBlock]:
    text = normalize_text("".join(storage.text))
    markers = [index for index, char in enumerate(text) if char == OBJECT_REPLACEMENT]
    entries = sorted(storage.table_attachment.entries, key=lambda entry: entry.character_index)
    if [entry.character_index for entry in entries] != markers:
        raise ValueError("Attachment positions do not match the body text")
    blocks: list[TextBlock | TableBlock] = []
    cursor = 0
    for index, entry in zip(markers, entries, strict=True):
        chunk = text[cursor:index].strip()
        if chunk:
            blocks.append(TextBlock(chunk))
        block = attachment_block(objects, entry.object.identifier)
        if block is not None:
            blocks.append(block)
        cursor = index + 1
    tail = text[cursor:].strip()
    if tail:
        blocks.append(TextBlock(tail))
    return blocks


def read_pages(data: bytes) -> PagesDocument:
    with zipfile.ZipFile(BytesIO(data)) as archive:
        objects = read_objects(archive)
        preview = archive.read("preview.jpg")
    return PagesDocument(document_blocks(objects, body_storage(objects)), preview)
