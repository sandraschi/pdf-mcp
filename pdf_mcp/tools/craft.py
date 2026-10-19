"""PdfCraft engine tool (Lane A headless).

Portmanteau over `pdf_mcp.services.pdfcraft_engine.PdfCraftEngine`.
Python-native ops (RAG, forms, redact-regex) stay in their own tools;
anything needing true rendering, merging, OCR/optimize, or redaction
audit delegates to the installed PdfCraft CLI.
"""

import logging
from typing import Annotated, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from pdf_mcp.server import mcp
from pdf_mcp.services.pdfcraft_engine import PdfCraftEngine
from pdf_mcp.tools._schema import TOOL_OUTPUT_SCHEMA

logger = logging.getLogger("pdf-mcp")

PdfCraftOperation = Literal[
    "status",
    "info",
    "render",
    "text",
    "combine",
    "extract",
    "split",
    "edit",
    "audit",
    "batch",
]


@mcp.tool(output_schema=TOOL_OUTPUT_SCHEMA, annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True))
async def pdf_craft(
    operation: PdfCraftOperation,
    path: Annotated[str | None, Field(description="Source PDF path. Ignored for status/combine/batch.")] = None,
    paths: Annotated[list[str] | None, Field(description="Input PDF list for combine/batch.")] = None,
    page: Annotated[int, Field(description="1-indexed page for render/text.")] = 1,
    dpi: Annotated[int, Field(description="Render DPI 36-600.")] = 96,
    pages: Annotated[str | None, Field(description="Page selector for extract, e.g. '1,3,5-8'.")] = None,
    every: Annotated[int, Field(description="Split every N pages.")] = 1,
    rotate: Annotated[str | None, Field(description="Rotate spec for edit, e.g. '1,3:90'.")] = None,
    delete: Annotated[str | None, Field(description="Delete spec for edit, e.g. '2,4'.")] = None,
    title: Annotated[str | None, Field(description="Set document title (edit).")] = None,
    author: Annotated[str | None, Field(description="Set document author (edit).")] = None,
    steps: Annotated[list[str] | None, Field(description="Batch steps subset of convert,ocr,optimize.")] = None,
    output_path: Annotated[str | None, Field(description="Optional explicit output path/dir. Auto-generated in data/pdfcraft/ if omitted.")] = None,
) -> dict:
    """Drive the installed PdfCraft engine (headless Lane A).

    status/info/text/audit are read-only; render/combine/extract/split/edit/batch
    write new files under data/pdfcraft/ and never modify inputs in place.
    Returns wrappee_missing (not a crash) when the CLI is not installed.

    ## Return Format

    A dict with keys:
    - success: bool
    - message: str - human-readable summary
    - operation-specific keys: path, files, out_dir, info, text, clean, version, cli
    On failure: {success: False, error, error_type} where error_type is one of
    wrappee_missing, InvalidInput, engine_error, engine_timeout.

    ## Examples

    >>> await pdf_craft(operation="status")
    {"success": true, "installed": true, "version": "pdfcraft-cli 0.9.0", ...}

    >>> await pdf_craft(operation="render", path="report.pdf", page=1)
    {"success": true, "path": "data/pdfcraft/report_p1_....png", ...}

    >>> await pdf_craft(operation="combine", paths=["a.pdf", "b.pdf"])
    {"success": true, "path": "data/pdfcraft/a_portfolio_....pdf", ...}

    >>> await pdf_craft(operation="audit", path="redacted.pdf")
    {"success": true, "clean": false, ...}
    """
    engine = PdfCraftEngine()
    try:
        if operation == "status":
            return engine.status()
        if operation == "info":
            if not path:
                return {"success": False, "error": "path required for info.", "error_type": "InvalidInput"}
            return engine.info(path)
        if operation == "text":
            if not path:
                return {"success": False, "error": "path required for text.", "error_type": "InvalidInput"}
            return engine.text(path, page=page if page else None)
        if operation == "render":
            if not path:
                return {"success": False, "error": "path required for render.", "error_type": "InvalidInput"}
            return engine.render(path, page=page, dpi=dpi, out_path=output_path)
        if operation == "combine":
            if not paths or len(paths) < 2:
                return {"success": False, "error": "combine needs paths with at least 2 PDFs.", "error_type": "InvalidInput"}
            return engine.combine(paths, out_path=output_path)
        if operation == "extract":
            if not path or not pages:
                return {"success": False, "error": "extract needs path and pages (e.g. '1,3,5-8').", "error_type": "InvalidInput"}
            return engine.extract_pages(path, pages, out_path=output_path)
        if operation == "split":
            if not path:
                return {"success": False, "error": "path required for split.", "error_type": "InvalidInput"}
            return engine.split_every(path, every=every, out_dir=output_path)
        if operation == "edit":
            if not path:
                return {"success": False, "error": "path required for edit.", "error_type": "InvalidInput"}
            return engine.edit(path, out_path=output_path, rotate=rotate, delete=delete, title=title, author=author)
        if operation == "audit":
            if not path:
                return {"success": False, "error": "path required for audit.", "error_type": "InvalidInput"}
            return engine.audit(path)
        if operation == "batch":
            if not paths:
                return {"success": False, "error": "batch needs paths.", "error_type": "InvalidInput"}
            return engine.batch(paths, steps=steps or ["convert", "ocr", "optimize"], out_dir=output_path)
        return {"success": False, "error": f"Unknown operation: {operation}", "error_type": "InvalidInput"}
    except Exception as e:
        logger.exception("pdf_craft %s failed: %s", operation, e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
