import hashlib
import logging
from pathlib import Path
from typing import Annotated

import numpy as np
from pydantic import Field

from pdf_mcp.config import cfg
from pdf_mcp.models import PdfRagOperation
from pdf_mcp.server import mcp
from pdf_mcp.services.chunker import Chunker
from pdf_mcp.services.rag_store import RagStore

logger = logging.getLogger("pdf-mcp")
chunker = Chunker()
rag_store = RagStore()


try:
    from sentence_transformers import SentenceTransformer

    _encoder = SentenceTransformer(cfg.rag_embedding_model)
    _use_st = True
except ImportError:
    _use_st = False


def _get_embedding(text: str) -> list[float]:
    if _use_st:
        try:
            return _encoder.encode(text).tolist()
        except Exception:
            pass
    vec = np.zeros(384, dtype=np.float32)
    h = hashlib.md5(text.encode())
    for i in range(384):
        h.update(str(i).encode())
        if int(h.hexdigest(), 16) % 2:
            vec[i] = 1.0
    return vec.tolist()


@mcp.tool()
async def pdf_rag(
    operation: PdfRagOperation,
    path: Annotated[str | None, Field(description="Path to the PDF file. Required for chunk, index operations.")] = None,
    strategy: Annotated[str, Field(description="Chunking strategy: recursive, fixed. Default recursive.")] = "recursive",
    chunk_size: Annotated[int, Field(description="Target chunk size in characters. Default 1000.")] = 1000,
    overlap: Annotated[int, Field(description="Chunk overlap in characters. Default 200.")] = 200,
    query: Annotated[str | None, Field(description="Search query for search operation.")] = None,
    limit: Annotated[int, Field(description="Max search results. Default 10.")] = 10,
    doc_id: Annotated[str | None, Field(description="Document ID for delete_index operation.")] = None,
) -> dict:
    try:
        if operation == "chunk":
            import fitz

            doc = fitz.open(path)
            try:
                full_text = "\n".join(page.get_text() for page in doc)
                page_count = len(doc)
            finally:
                doc.close()
            chunks = chunker.chunk(full_text, strategy=strategy, chunk_size=chunk_size, overlap=overlap)
            doc_id = hashlib.md5(path.encode()).hexdigest()[:12]
            return {
                "success": True,
                "chunks": len(chunks),
                "doc_id": doc_id,
                "message": f"Chunked {Path(path).name} ({page_count} pages) into {len(chunks)} chunks with {strategy} strategy.",
            }

        elif operation == "index":
            import fitz

            doc = fitz.open(path)
            try:
                full_text = "\n".join(page.get_text() for page in doc)
                page_count = len(doc)
            finally:
                doc.close()
            chunks = chunker.chunk(full_text, strategy=strategy, chunk_size=chunk_size, overlap=overlap)
            doc_id = hashlib.md5(path.encode()).hexdigest()[:12]
            indexed = rag_store.index_document(doc_id=doc_id, text=full_text, chunks=chunks, embedding_fn=_get_embedding)
            return {
                "success": True,
                "chunks_indexed": indexed,
                "doc_id": doc_id,
                "message": f"Indexed {Path(path).name} ({page_count} pages, {indexed} chunks) from {Path(path).name}.",
            }

        elif operation == "search":
            results = rag_store.search(query=query or "", limit=limit, embedding_fn=_get_embedding)
            return {"success": True, "results": results, "message": f"Found {len(results)} results for '{query}'."}

        elif operation == "list_documents":
            documents = rag_store.list_documents()
            return {"success": True, "documents": documents, "message": f"Found {len(documents)} indexed document(s)."}

        elif operation == "delete_index":
            rag_store.delete_document(doc_id=doc_id or "")
            return {"success": True, "message": f"Deleted indexed document {doc_id}."}
    except Exception as e:
        logger.exception("pdf_rag %s failed: %s", operation, e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
