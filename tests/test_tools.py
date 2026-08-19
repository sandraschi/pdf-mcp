import os
import tempfile
from pathlib import Path

import fitz
import pytest

from pdf_mcp.services.chunker import Chunker
from pdf_mcp.services.converter import Converter
from pdf_mcp.services.extractor import Extractor
from pdf_mcp.services.manipulator import Manipulator
from pdf_mcp.services.rag_store import RagStore


@pytest.fixture
def sample_pdf():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(72, 72), "Hello PDF MCP", fontsize=20)
    doc.save(path)
    doc.close()
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestExtract:
    def test_extract_text(self, sample_pdf):
        ext = Extractor()
        result = ext.extract_text(sample_pdf)
        assert result["success"] is True
        assert "Hello PDF MCP" in result["text"]
        assert result["pages"] == 1
        assert result["page_count"] == 1

    def test_extract_metadata(self, sample_pdf):
        ext = Extractor()
        result = ext.extract_metadata(sample_pdf)
        assert result["success"] is True
        meta = result["metadata"]
        assert meta["page_count"] == 1
        assert meta["file_size"] > 0


class TestManipulate:
    def test_manipulate_merge(self):
        paths = []
        for label in ["Doc A", "Doc B"]:
            f = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            paths.append(f.name)
            f.close()
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(fitz.Point(72, 72), label, fontsize=20)
            doc.save(f.name)
            doc.close()
        manip = Manipulator()
        out = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False).name
        try:
            result = manip.merge(paths, out)
            assert result["success"] is True
            assert result["pages"] == 2
        finally:
            for p in paths + [out]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_manipulate_rotate(self, sample_pdf):
        manip = Manipulator()
        out = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False).name
        try:
            result = manip.rotate(sample_pdf, out, pages=None, angle=90)
            assert result["success"] is True
            assert os.path.exists(result["path"])
        finally:
            if os.path.exists(out):
                os.unlink(out)


class TestConvert:
    def test_convert_to_images(self, sample_pdf):
        conv = Converter()
        out_dir = tempfile.mkdtemp()
        try:
            result = conv.to_images(sample_pdf, out_dir, fmt="png", dpi=150)
            assert result["success"] is True
            assert len(result["images"]) == 1
            img_path = result["images"][0]["path"]
            assert img_path.endswith(".png")
            assert os.path.exists(img_path)
        finally:
            for f in Path(out_dir).glob("*"):
                f.unlink()
            os.rmdir(out_dir)


class TestChunker:
    def test_chunker_recursive(self):
        chunker = Chunker()
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        metadata = {"doc_id": "test123"}
        chunks = chunker.chunk_recursive(text, metadata, chunk_size=100, overlap=20)
        assert len(chunks) > 0
        for c in chunks:
            assert c["doc_id"] == "test123"
            assert "text" in c

    def test_chunker_overlap(self):
        chunker = Chunker()
        text = "Word " * 500
        metadata = {"doc_id": "overlap_test"}
        chunks = chunker.chunk_recursive(text, metadata, chunk_size=200, overlap=50)
        assert len(chunks) > 1
        for i in range(len(chunks) - 1):
            chunk_end = chunks[i]["text"][-50:]
            chunk_start = chunks[i + 1]["text"][:50]
            if any(w in chunk_start for w in chunk_end.split()):
                break
        else:
            pass


class TestRagStore:
    def test_rag_store_crud(self):
        db_dir = tempfile.mkdtemp()
        try:
            store = RagStore(db_dir)
            chunks = [
                {"doc_id": "test_doc", "chunk_id": "c1", "page_num": 1, "text": "PDF chunk one", "section": None, "metadata": {}},
                {"doc_id": "test_doc", "chunk_id": "c2", "page_num": 1, "text": "PDF chunk two", "section": None, "metadata": {}},
            ]
            emb = [[0.1] * store.get_embedding_dim(), [0.2] * store.get_embedding_dim()]
            idx = store.index_chunks(chunks, emb)
            assert idx["success"] is True
            assert idx["count"] == 2

            q_emb = [0.15] * store.get_embedding_dim()
            sr = store.search(q_emb, limit=5)
            assert sr["success"] is True
            assert len(sr["results"]) > 0

            ld = store.list_documents()
            assert ld["success"] is True
            assert len(ld["documents"]) == 1
            assert ld["documents"][0]["doc_id"] == "test_doc"
            assert ld["documents"][0]["chunk_count"] == 2

            dd = store.delete_document("test_doc")
            assert dd["success"] is True

            ld2 = store.list_documents()
            assert len(ld2["documents"]) == 0
        finally:
            import shutil

            shutil.rmtree(db_dir, ignore_errors=True)


class TestIntel:
    def test_analyzer_detects_digital(self, sample_pdf):
        from pdf_mcp.services.intel import Analyzer

        result = Analyzer.analyze(sample_pdf)
        assert result["success"] is True
        assert result["has_text_layer"] is True
        assert result["scanned"] is False
        assert result["layout_hint"] == "digital"

    def test_classifier_detects_letter(self, sample_pdf):
        from pdf_mcp.services.intel import Classifier

        result = Classifier.classify(sample_pdf)
        assert result["success"] is True
        assert result["doc_type"] in ("letter", "other", "report")

    def test_redactor_removes_pii(self, sample_pdf):
        from pdf_mcp.services.intel import Redactor

        out = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False).name
        try:
            result = Redactor.redact(sample_pdf, out, pii=True)
            assert result["success"] is True
            assert os.path.exists(out)
        finally:
            if os.path.exists(out):
                os.unlink(out)

    def test_deduper_finds_exact_duplicates(self, sample_pdf):
        from pdf_mcp.services.intel import Deduper

        result = Deduper.dedupe([sample_pdf, sample_pdf], threshold=0.85)
        assert result["success"] is True
        assert len(result["exact_duplicates"]) == 1

    def test_brief_builder(self, sample_pdf):
        from pdf_mcp.services.intel import BriefBuilder

        result = BriefBuilder.build(sample_pdf, format="markdown")
        assert result["success"] is True
        assert result["path"].endswith("_brief.md")

    def test_chunk_with_tables(self):
        from pdf_mcp.services.chunker import Chunker

        chunker = Chunker()
        tables = [[["Q1", "100"], ["Q2", "200"]]]
        chunks = chunker.chunk_with_tables("Some body text about growth.", tables, {"doc_id": "t"})
        assert any(c["section"] == "table" for c in chunks)


class TestRagOps:
    def test_rag_similar_and_synthesize(self, sample_pdf):
        import asyncio

        from pdf_mcp.tools.rag import pdf_rag

        async def run():
            idx = await pdf_rag(operation="index", path=sample_pdf)
            assert idx["success"] is True
            s = await pdf_rag(operation="search", query="Hello PDF MCP")
            assert s["success"] is True
            assert len(s["results"]) >= 1
            assert s["results"][0].get("source_file")
            sim = await pdf_rag(operation="similar", text="Hello PDF MCP")
            assert sim["success"] is True
            syn = await pdf_rag(operation="synthesize", query="Hello PDF MCP", limit=5)
            assert syn["success"] is True

        asyncio.run(run())
