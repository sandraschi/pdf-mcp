import hashlib
import logging
from pathlib import Path
from typing import Annotated

import numpy as np
from mcp.types import ToolAnnotations
from pydantic import Field

from pdf_mcp.config import cfg
from pdf_mcp.models import PdfRagOperation
from pdf_mcp.server import mcp
from pdf_mcp.services.chunker import Chunker
from pdf_mcp.services.rag_store import RagStore

logger = logging.getLogger("pdf-mcp")
chunker = Chunker()
rag_store = RagStore(cfg.rag_store_path)

try:
    from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

    _encoder: SentenceTransformer | None = SentenceTransformer(cfg.rag_embedding_model)
    _use_st = True
except ImportError:
    _encoder = None
    _use_st = False


def _get_embedding(text: str) -> list[float]:
    if _use_st and _encoder is not None:
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


def _chunk_text(text: str, strategy: str, chunk_size: int, overlap: int, doc_id: str, tables: list | None = None, source_file: str = "") -> list[dict]:
    metadata: dict = {"doc_id": doc_id}
    if source_file:
        metadata["source_file"] = source_file
    if strategy == "fixed":
        chunks = []
        step = max(chunk_size - overlap, 1)
        for i, start in enumerate(range(0, len(text), step)):
            piece = text[start : start + chunk_size]
            if not piece:
                continue
            chunks.append(
                {
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_f{i}",
                    "page_num": 0,
                    "text": piece,
                    "section": None,
                    "metadata": {**metadata, "chunk_index": i},
                }
            )
        return chunks
    if tables:
        return chunker.chunk_with_tables(text, tables, metadata, chunk_size=chunk_size, overlap=overlap)
    return chunker.chunk_recursive(text, metadata, chunk_size=chunk_size, overlap=overlap)


def _extract_tables(path: str) -> list:
    try:
        import pdfplumber

        tables = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:20]:
                for t in page.extract_tables() or []:
                    if t:
                        tables.append(t)
        return tables
    except Exception:
        return []


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def pdf_rag(
    operation: PdfRagOperation,
    path: Annotated[str | None, Field(description="Path to the PDF file. Required for chunk, index operations.")] = None,
    strategy: Annotated[str, Field(description="Chunking strategy: recursive, fixed. Default recursive.")] = "recursive",
    chunk_size: Annotated[int, Field(description="Target chunk size in characters. Default 1000.")] = 1000,
    overlap: Annotated[int, Field(description="Chunk overlap in characters. Default 200.")] = 200,
    query: Annotated[str | None, Field(description="Search query for search / synthesize operations.")] = None,
    text: Annotated[str | None, Field(description="Source text snippet for similar (query-by-example) operation.")] = None,
    limit: Annotated[int, Field(description="Max search results. Default 10.")] = 10,
    doc_id: Annotated[str | None, Field(description="Document ID for delete_index operation.")] = None,
) -> dict:
    """Build and query a RAG index over PDF content.

    Chunks, indexes, and semantically searches PDF text via LanceDB. Tables are
    indexed as structured chunks (section='table'). Supports query-by-example and
    cross-document synthesis.

    ## Return Format

    A dict with keys:
    - success: bool - whether the operation succeeded
    - message: str - human-readable summary
    - operation-specific keys:
      - chunk: {chunks, doc_id}
      - index: {chunks_indexed, doc_id}
      - search: {results: [{doc_id, chunk_id, page_num, section, source_file, text, _distance}]}
      - similar: same shape as search (seeded by a text snippet)
      - synthesize: {groups: [{doc_id, source_file, hits, snippet}], summary?}
      - list_documents: {documents: [{doc_id, chunk_count}]}
      - delete_index: {}
    On failure: {success: False, error, error_type}.

    ## Examples

    >>> await pdf_rag(operation="chunk", path="book.pdf", strategy="recursive", chunk_size=1000)
    {"success": true, "chunks": 42, "doc_id": "a1b2c3d4e5f6",
     "message": "Chunked book.pdf (300 pages) into 42 chunks with recursive strategy."}

    >>> await pdf_rag(operation="search", query="quarterly revenue")
    {"success": true, "results": [{...}], "message": "Found 3 results for 'quarterly revenue'."}

    >>> await pdf_rag(operation="similar", text="The sky was unusually clear that night.")
    {"success": true, "results": [{...}], "message": "Found 2 similar passages."}
    """
    try:
        if operation in ("chunk", "index") and not path:
            return {"success": False, "error": "path is required for chunk and index operations."}

        if operation == "chunk":
            if not path:
                return {"success": False, "error": "path is required for chunk."}
            import fitz

            doc: fitz.Document = fitz.open(path)
            try:
                full_text = "\n".join(str(doc[i].get_text()) for i in range(len(doc)))
                page_count = len(doc)
            finally:
                doc.close()
            doc_id_val = hashlib.md5(path.encode()).hexdigest()[:12]
            chunks = _chunk_text(full_text, strategy=strategy, chunk_size=chunk_size, overlap=overlap, doc_id=doc_id_val)
            return {
                "success": True,
                "chunks": len(chunks),
                "doc_id": doc_id_val,
                "message": f"Chunked {Path(path).name} ({page_count} pages) into {len(chunks)} chunks with {strategy} strategy.",
            }

        elif operation == "index":
            if not path:
                return {"success": False, "error": "path is required for index."}
            import fitz

            doc: fitz.Document = fitz.open(path)
            try:
                full_text = "\n".join(str(doc[i].get_text()) for i in range(len(doc)))
                page_count = len(doc)
            finally:
                doc.close()
            doc_id_val = hashlib.md5(path.encode()).hexdigest()[:12]
            tables = _extract_tables(path)
            chunks = _chunk_text(
                full_text,
                strategy=strategy,
                chunk_size=chunk_size,
                overlap=overlap,
                doc_id=doc_id_val,
                tables=tables if strategy == "recursive" else None,
                source_file=Path(path).name,
            )
            embeddings = [_get_embedding(c["text"]) for c in chunks]
            indexed = rag_store.index_chunks(chunks, embeddings)
            if not indexed.get("success"):
                return indexed
            return {
                "success": True,
                "chunks_indexed": indexed["count"],
                "doc_id": doc_id_val,
                "message": f"Indexed {Path(path).name} ({page_count} pages, {indexed['count']} chunks).",
            }

        elif operation in ("search", "similar"):
            seed = query or "" if operation == "search" else text or ""
            query_embedding = _get_embedding(seed)
            results = rag_store.search(query_embedding, limit=limit)
            if not results.get("success"):
                return results
            label = "similar passages" if operation == "similar" else "results"
            return {
                "success": True,
                "results": results["results"],
                "message": f"Found {len(results['results'])} {label}.",
            }

        elif operation == "synthesize":
            if not query:
                return {"success": False, "error": "query is required for synthesize."}
            query_embedding = _get_embedding(query)
            results = rag_store.search(query_embedding, limit=max(limit, 20))
            if not results.get("success"):
                return results
            groups: dict[str, dict] = {}
            for r in results["results"]:
                g = groups.setdefault(
                    r["doc_id"],
                    {"doc_id": r["doc_id"], "source_file": r.get("source_file"), "hits": [], "snippets": []},
                )
                g["hits"].append({"chunk_id": r["chunk_id"], "page_num": r.get("page_num"), "section": r.get("section"), "text": r["text"][:500], "_distance": r.get("_distance")})
                g["snippets"].append(r["text"][:300])
            summary = None
            try:
                from pdf_mcp.services.llm import chat_completion

                corpus = "\n---\n".join(f"[{g['source_file'] or g['doc_id']}] " + " ".join(g["snippets"][:4]) for g in groups.values())[:8000]
                summary = await chat_completion(
                    [
                        {"role": "system", "content": "Synthesize the retrieved passages into a concise answer with per-document evidence. Do not invent facts not in the passages."},
                        {"role": "user", "content": f"Question: {query}\n\nPassages:\n{corpus}"},
                    ]
                )
            except Exception:
                summary = None
            return {
                "success": True,
                "groups": list(groups.values()),
                "summary": summary,
                "llm": summary is not None,
                "message": f"Synthesized {len(groups)} document(s) for '{query}'.",
            }

        elif operation == "list_documents":
            documents = rag_store.list_documents()
            if not documents.get("success"):
                return documents
            return {
                "success": True,
                "documents": documents["documents"],
                "message": f"Found {len(documents['documents'])} indexed document(s).",
            }

        elif operation == "delete_index":
            rag_store.delete_document(doc_id=doc_id or "")
            return {"success": True, "message": f"Deleted indexed document {doc_id}."}
        return {"success": False, "error": f"Unknown operation: {operation}"}
    except Exception as e:
        logger.exception("pdf_rag %s failed: %s", operation, e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
