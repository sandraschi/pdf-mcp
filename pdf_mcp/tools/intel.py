import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from mcp.types import ToolAnnotations
from pydantic import Field

from pdf_mcp.config import cfg
from pdf_mcp.server import mcp
from pdf_mcp.services.intel import Analyzer, BriefBuilder, Classifier, Deduper, Redactor
from pdf_mcp.services.llm import chat_completion
from pdf_mcp.tools._schema import TOOL_OUTPUT_SCHEMA

logger = logging.getLogger("pdf-mcp")


def _out_path(path: str, op: str) -> str:
    p = Path(path)
    cfg.upload_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    return str(cfg.upload_dir / f"{p.stem}_{op}_{ts}_{uid}.pdf")


@mcp.tool(output_schema=TOOL_OUTPUT_SCHEMA, app=True, annotations=ToolAnnotations(readOnlyHint=True))
async def pdf_analyze(path: Annotated[str, Field(description="Path to the PDF file.")]) -> dict:
    """Detect whether a PDF has a text layer (digital) or is scanned, with layout stats.

    ## Return Format

    A dict with keys:
    - success: bool
    - pages: int
    - has_text_layer: bool - true when average chars per page >= 80
    - scanned: bool - low text + images present
    - chars_per_page: float
    - total_chars: int
    - image_count: int
    - layout_hint: str - digital | scanned | empty
    - per_page: list of {page, chars, images}

    ## Examples

    >>> await pdf_analyze(path="scan.pdf")
    {"success": true, "pages": 5, "has_text_layer": false, "scanned": true,
     "chars_per_page": 12.4, "image_count": 5, "layout_hint": "scanned", "per_page": [...]}
    """
    return Analyzer.analyze(path)


@mcp.tool(output_schema=TOOL_OUTPUT_SCHEMA, annotations=ToolAnnotations(destructiveHint=True, openWorldHint=True))
async def pdf_redact(
    path: Annotated[str, Field(description="Path to the PDF file to redact.")],
    terms: Annotated[list[str] | None, Field(description="Exact phrases to blacken.")] = None,
    pii: Annotated[bool, Field(description="Redact PII (email, phone, IBAN, card, SSN, IP). Default false.")] = False,
    output_path: Annotated[str | None, Field(description="Output path. Auto-generated if omitted.")] = None,
) -> dict:
    """Blacken sensitive content in a PDF by terms and/or PII patterns.

    ## Return Format

    A dict with keys:
    - success: bool
    - path: str - output PDF path
    - occurrences: int - number of regions redacted
    On failure: {success: False, error}.

    ## Examples

    >>> await pdf_redact(path="report.pdf", pii=True)
    {"success": true, "path": ".../report_redact_....pdf", "occurrences": 7}

    >>> await pdf_redact(path="report.pdf", terms=["Acme Corp"])
    {"success": true, "path": ".../report_redact_....pdf", "occurrences": 3}
    """
    try:
        op = output_path or _out_path(path, "redact")
        result = Redactor.redact(path, op, terms=terms, pii=pii)
        if not result.get("success"):
            return result
        return {
            "success": True,
            "path": result["path"],
            "occurrences": result["occurrences"],
            "message": f"Redacted {result['occurrences']} region(s) from {Path(path).name}.",
        }
    except Exception as e:
        logger.exception("pdf_redact failed: %s", e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


@mcp.tool(output_schema=TOOL_OUTPUT_SCHEMA, app=True, annotations=ToolAnnotations(readOnlyHint=True))
async def pdf_classify(
    path: Annotated[str, Field(description="Path to the PDF file.")],
    refine: Annotated[bool, Field(description="Use the local LLM to refine the guess. Default true.")] = True,
) -> dict:
    """Guess the document type (invoice, report, contract, ...) and extract candidate fields.

    ## Return Format

    A dict with keys:
    - success: bool
    - doc_type: str
    - confidence: float (0-1)
    - fields: dict of detected fields (invoice_number, total, date, vendor)
    - reasons: list of matched signals
    - llm_refined: bool - whether the local LLM confirmed the guess

    ## Examples

    >>> await pdf_classify(path="invoice_42.pdf")
    {"success": true, "doc_type": "invoice", "confidence": 0.75,
     "fields": {"invoice_number": "INV-42", "total": "1,240.00"}, "reasons": ["invoice(x2)"]}
    """
    try:
        result = Classifier.classify(path)
        if not result.get("success"):
            return result
        llm_refined = False
        if refine:
            try:
                verdict = await chat_completion(
                    [
                        {
                            "role": "system",
                            "content": "You classify documents. Reply with a single word: one of invoice, receipt, report, contract, form, resume, presentation, letter, scanned-document, or other. Reply with only that word.",
                        },
                        {"role": "user", "content": f"Heuristic says: {result['doc_type']}. Signals: {result.get('reasons')}. First-page excerpt: {(result.get('title') or '')[:200]}"},
                    ]
                )
                candidate = verdict.strip().lower().split()[0] if verdict.strip() else ""
                if candidate in DOC_TYPES:
                    result["doc_type"] = candidate
                    llm_refined = True
            except Exception:
                pass
        return {**result, "llm_refined": llm_refined}
    except Exception as e:
        logger.exception("pdf_classify failed: %s", e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


DOC_TYPES = {
    "invoice",
    "receipt",
    "report",
    "contract",
    "form",
    "resume",
    "presentation",
    "letter",
    "scanned-document",
    "other",
}


@mcp.tool(output_schema=TOOL_OUTPUT_SCHEMA, app=True, annotations=ToolAnnotations(readOnlyHint=True))
async def pdf_dedupe(
    paths: Annotated[list[str], Field(description="List of PDF paths to check for duplicates.")],
    threshold: Annotated[float, Field(description="Similarity threshold 0-1. Default 0.85.")] = 0.85,
) -> dict:
    """Detect exact and near-duplicate PDFs by content fingerprint.

    ## Return Format

    A dict with keys:
    - success: bool
    - files: list of input file names
    - exact_duplicates: [{sha, count, files}]
    - near_duplicates: [{a, b, similarity}]

    ## Examples

    >>> await pdf_dedupe(paths=["a.pdf", "b.pdf"])
    {"success": true, "files": ["a.pdf", "b.pdf"], "exact_duplicates": [],
     "near_duplicates": [{"a": "a.pdf", "b": "b.pdf", "similarity": 0.92}]}
    """
    try:
        return Deduper.dedupe(paths, threshold=threshold)
    except Exception as e:
        logger.exception("pdf_dedupe failed: %s", e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


@mcp.tool(output_schema=TOOL_OUTPUT_SCHEMA, annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True))
async def pdf_export(
    path: Annotated[str, Field(description="Path to the PDF file.")],
    format: Annotated[Literal["markdown", "json"], Field(description="Output format. Default markdown.")] = "markdown",
    include_summary: Annotated[bool, Field(description="Append an LLM summary when available. Default true.")] = True,
) -> dict:
    """Build a reusable document brief (markdown or JSON) with headings, key terms, and optional summary.

    ## Return Format

    A dict with keys:
    - success: bool
    - path: str - brief file path
    - pages: int
    - summary: str | None

    ## Examples

    >>> await pdf_export(path="report.pdf", format="markdown")
    {"success": true, "path": ".../report_brief.md", "pages": 12, "summary": "..."}
    """
    try:
        llm_summary = None
        if include_summary:
            try:
                doc_text = ""
                import fitz

                d = fitz.open(path)
                try:
                    doc_text = " ".join(str(d[i].get_text()) for i in range(min(len(d), 8)))
                finally:
                    d.close()
                llm_summary = await chat_completion(
                    [
                        {"role": "system", "content": "Write a 3-5 sentence summary of the document. Be factual and specific."},
                        {"role": "user", "content": doc_text[:6000]},
                    ]
                )
            except Exception:
                llm_summary = None
        result = BriefBuilder.build(path, format=format, include_summary=include_summary, llm_summary=llm_summary)
        if not result.get("success"):
            return result
        return {
            "success": True,
            "path": result["path"],
            "pages": result["pages"],
            "summary": result.get("summary"),
            "message": f"Exported brief for {Path(path).name} to {Path(result['path']).name}.",
        }
    except Exception as e:
        logger.exception("pdf_export failed: %s", e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
