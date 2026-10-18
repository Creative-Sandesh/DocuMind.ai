import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from PIL import Image

from app.services import document_service, marker_service
from app.services.chunking_service import iter_structured_chunks
from app.services.marker_service import ParsedBlock, ParsedPage, ParsedPdf, parse_marker_output


class MarkerStructureTests(unittest.TestCase):
    def test_headings_table_equation_and_original_pages(self):
        parsed = parse_marker_output(
            {"metadata": {"page_stats": [
                {"text_extraction_method": "pdftext"},
                {"text_extraction_method": "pdftext"},
                {"text_extraction_method": "ocr"},
            ]}, "children": [
                {"children": [
                    {"block_type": "SectionHeader", "html": "<h1>Energy</h1>"},
                    {"block_type": "Text", "html": "<p>Energy is conserved.</p>"},
                    {"block_type": "Table", "html": "<table><tr><th>Form</th><th>Unit</th></tr><tr><td><content-ref src='cell-1'></content-ref></td><td><content-ref src='cell-2'></content-ref></td></tr></table>",
                     "children": [{"id": "cell-1", "block_type": "TableCell", "html": "Heat"},
                                  {"id": "cell-2", "block_type": "TableCell", "html": "J"}]},
                    {"block_type": "Equation", "html": "<math display='block'>E = mc²</math>"},
                    {"block_type": "Figure", "html": "<figure><img src='data:image/png;base64,AAAA' alt='Energy graph'/><figcaption>Energy rises</figcaption></figure>"},
                ]},
                {"children": []},
                {"children": [{"block_type": "Text", "html": "<p>Later evidence</p>"}]},
            ]},
            {"markdown": "# Energy", "images": {"figure.jpeg": Image.new("RGB", (2, 2))}},
        )
        self.assertEqual(len(parsed.pages), 3)
        self.assertEqual(parsed.pages[2].extraction_method, "ocr")
        self.assertIn("| Heat | J |", parsed.pages[0].blocks[1].text)
        self.assertIn("E = mc²", parsed.pages[0].blocks[2].text)
        self.assertIn("$$", parsed.pages[0].blocks[2].text)
        self.assertIn("Energy rises", parsed.pages[0].blocks[3].text)
        self.assertNotIn("base64", parsed.pages[0].blocks[3].text)
        self.assertTrue(parsed.images["figure.jpeg"].startswith(b"\xff\xd8"))
        chunks = list(iter_structured_chunks(parsed.pages, "doc"))
        self.assertEqual([chunk["page_number"] for chunk in chunks], [1, 1, 1, 1, 3])
        self.assertEqual([chunk["block_type"] for chunk in chunks[:4]], ["Text", "Table", "Equation", "Figure"])
        self.assertTrue(all(chunk["section_title"] == "Energy" for chunk in chunks))

    def test_large_block_splits_with_valid_citations(self):
        page = ParsedPage(7, (ParsedBlock("Table", "row value\n" * 220, "Measurements"),))
        chunks = list(iter_structured_chunks((page,), "doc", chunk_size=120, chunk_overlap=20))
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk["page_number"] == 7 and len(chunk["text"]) <= 120 for chunk in chunks))

    def test_artifacts_and_cleanup_include_images(self):
        parsed = ParsedPdf(
            pages=(ParsedPage(1, (ParsedBlock("Text", "A caption", "Figures"),)),),
            markdown="![figure](figure.jpeg)",
            images={"figure.jpeg": b"jpeg-bytes"},
        )
        with tempfile.TemporaryDirectory() as directory, patch.object(
            document_service, "DOCUMENT_DIR", Path(directory)
        ):
            document_service.save_marker_artifacts("abc", parsed)
            structure = json.loads((Path(directory) / "fileabc.marker.json").read_text(encoding="utf-8"))
            image_name = structure["images"]["figure.jpeg"]
            self.assertTrue((Path(directory) / image_name).exists())
            self.assertIn(image_name, (Path(directory) / "fileabc.marker.md").read_text(encoding="utf-8"))
            document_service.remove_document_artifacts("abc")
            self.assertEqual(list(Path(directory).iterdir()), [])


class MarkerFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_local_models_return_503_and_remove_upload(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            document_service, "DOCUMENT_DIR", Path(directory)
        ), patch.object(document_service, "convert_pdf", side_effect=marker_service.MarkerUnavailableError("models missing")):
            with self.assertRaises(HTTPException) as raised:
                await document_service.process_document(
                    UploadFile(filename="book.pdf", file=io.BytesIO(b"%PDF"))
                )
            self.assertEqual(raised.exception.status_code, 503)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
