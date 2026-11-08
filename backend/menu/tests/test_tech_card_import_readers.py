import zipfile
from io import BytesIO
from pathlib import Path

from django.test import SimpleTestCase

from menu.tech_card_import.docx_reader import docx_blocks
from menu.tech_card_import.markdown import render_markdown
from menu.tech_card_import.pages_reader import read_pages

FILES = Path(__file__).resolve().parent / "files"

MERGED_DOCX = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Заголовок</w:t></w:r></w:p>
    <w:tbl>
      <w:tblGrid><w:gridCol/><w:gridCol/><w:gridCol/></w:tblGrid>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Мед</w:t></w:r></w:p></w:tc>
        <w:tc>
          <w:tcPr><w:gridSpan w:val="2"/></w:tcPr>
          <w:p><w:r><w:t>100</w:t></w:r></w:p>
        </w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Сахар</w:t></w:r></w:p></w:tc>
        <w:tc>
          <w:tcPr><w:vMerge/></w:tcPr>
          <w:p><w:r><w:t>скрыто</w:t></w:r></w:p>
        </w:tc>
        <w:tc>
          <w:tcPr><w:vMerge w:val="continue"/></w:tcPr>
          <w:p><w:r><w:t>тоже скрыто</w:t></w:r></w:p>
        </w:tc>
      </w:tr>
    </w:tbl>
  </w:body>
</w:document>
"""


def merged_docx() -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", MERGED_DOCX)
    return buffer.getvalue()


class TechCardImportReaderTests(SimpleTestCase):
    def test_docx_medovik(self):
        markdown = render_markdown(docx_blocks((FILES / "medovik.docx").read_bytes()))
        self.assertIn("МЕДОВИК", markdown)
        self.assertIn("Медовые коржи", markdown)
        self.assertIn("1000", markdown)
        self.assertIn("СБОРКА", markdown)
        self.assertIn("Измельчить медовые коржи", markdown)

    def test_docx_lime(self):
        markdown = render_markdown(docx_blocks((FILES / "lime.docx").read_bytes()))
        self.assertIn("КОРПУСНЫЕ ПИРОЖНЫЕ", markdown)
        self.assertIn("Цукаты из лайма", markdown)
        self.assertIn("Корки лайма", markdown)
        self.assertIn("65", markdown)
        self.assertIn("Срезать с лаймов корки", markdown)

    def test_docx_merged_cells_keep_the_anchor_text_once(self):
        markdown = render_markdown(docx_blocks(merged_docx()))
        self.assertIn("Заголовок", markdown)
        self.assertIn("| Мед | 100 |  |", markdown)
        self.assertIn("| Сахар |  |  |", markdown)
        self.assertNotIn("скрыто", markdown)

    def test_pages_mango(self):
        document = read_pages((FILES / "mango.pages").read_bytes())
        self.assertTrue(document.preview.startswith(b"\xff\xd8"))
        markdown = render_markdown(document.blocks)
        self.assertIn("Манго", markdown)
        self.assertIn("Пюре манго", markdown)
        self.assertIn("160", markdown)
        self.assertIn("Сборка", markdown)
        self.assertEqual(markdown.count("Пектин смешать с сахаром"), 1)

    def test_pages_lime(self):
        document = read_pages((FILES / "lime.pages").read_bytes())
        self.assertTrue(document.preview.startswith(b"\xff\xd8"))
        markdown = render_markdown(document.blocks)
        self.assertIn("КОРПУСНЫЕ ПИРОЖНЫЕ", markdown)
        self.assertIn("Цукаты из лайма", markdown)
        self.assertIn("Корки лайма", markdown)
        self.assertIn("65", markdown)
        self.assertIn("Срезать с лаймов корки", markdown)
