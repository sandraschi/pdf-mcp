"""FastMCP prompts and resources.

- `@mcp.prompt()` templates for common workflows (M6).
- `@mcp.resource()` for live config/status (M5).
The skill directory is registered as a `SkillsDirectoryProvider` in server.py
(exposes `skill://pdf-expert`).
"""

import json
import time

from pdf_mcp.config import cfg
from pdf_mcp.server import mcp

_SERVER_START = time.time()


# ── Prompts (workflow templates) ──


@mcp.prompt()
def analyze_document(path: str) -> str:
    """Analyze a PDF: type, OCR readiness, and a summary."""
    return (
        "You are analyzing a PDF document with pdf-mcp. Run these tools and report findings:\n"
        f"1. pdf_analyze(path={path!r}) - is it scanned or digital?\n"
        f"2. pdf_classify(path={path!r}) - what kind of document is it?\n"
        f"3. pdf_export(path={path!r}) - build a brief with a summary.\n"
        "Synthesize the results into a short report with concrete numbers."
    )


@mcp.prompt()
def summarize_document(path: str, format: str = "markdown") -> str:
    """Summarize a PDF into a reusable brief."""
    return f"Summarize the PDF at {path!r} using pdf_export(path={path!r}, format={format!r}, include_summary=True). Return the path of the generated brief and a short overview."


@mcp.prompt()
def extract_tables(path: str) -> str:
    """Extract all tables from a PDF."""
    return f"Extract every table from {path!r} with pdf_extract(operation='tables', path={path!r}). List each table with its page, row/column count, and the header row."


@mcp.prompt()
def rag_question(query: str) -> str:
    """Ask a question across the indexed PDFs."""
    return (
        f"Answer this question using the RAG index: {query!r}\n"
        f"Run pdf_rag(operation='search', query={query!r}, limit=10), then "
        "pdf_rag(operation='synthesize', query={query!r}, limit=10) if available. "
        "Cite the source file and page numbers for each claim."
    )


@mcp.prompt()
def redact_review(path: str) -> str:
    """Check a PDF for PII and redact it."""
    return (
        f"Review {path!r} for sensitive data. Run pdf_analyze(path={path!r}) to confirm it has a text "
        f"layer, then pdf_redact(path={path!r}, pii=True). Report how many regions were redacted and "
        "the output path."
    )


@mcp.prompt()
def compare_documents(path_a: str, path_b: str) -> str:
    """Compare two PDFs and summarize the differences."""
    return (
        f"Compare {path_a!r} and {path_b!r} with pdf_validate(operation='compare', path_a={path_a!r}, "
        f"path_b={path_b!r}). Report page-count differences, text similarity, and the most important "
        "differences."
    )


# ── Resources (live config / status) ──


@mcp.resource("config://server")
def server_config() -> str:
    """Server configuration snapshot."""
    return json.dumps(
        {
            "server": cfg.server_name,
            "version": cfg.version,
            "mode": cfg.mode,
            "host": cfg.host,
            "port": cfg.port,
            "frontend_port": cfg.frontend_port,
            "upload_dir": str(cfg.upload_dir),
            "rag_store_path": str(cfg.rag_store_path),
            "is_tauri": cfg.is_tauri,
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.resource("status://server")
async def server_status() -> str:
    """Live server status (tool count, uptime)."""
    tools = await mcp.list_tools()
    return json.dumps(
        {
            "status": "ok",
            "server": cfg.server_name,
            "version": cfg.version,
            "tool_count": len(tools),
            "mode": cfg.mode,
            "uptime_seconds": int(time.time() - _SERVER_START),
        },
        indent=2,
        ensure_ascii=False,
    )
