import difflib
import logging
from pathlib import Path
from typing import Annotated, Any, cast

import fitz
from mcp.types import ToolAnnotations
from pydantic import Field

from pdf_mcp.models import PdfValidateOperation
from pdf_mcp.server import mcp

logger = logging.getLogger("pdf-mcp")


def _get_text(path: str) -> str:
    doc = fitz.open(path)
    try:
        return "\n".join(str(page.get_text()) for page in doc)
    finally:
        doc.close()


def _page_count(path: str) -> int:
    doc = fitz.open(path)
    try:
        return len(doc)
    finally:
        doc.close()


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def pdf_validate(
    operation: PdfValidateOperation,
    path: Annotated[str, Field(description="Path to the PDF file. Ignored for compare.")],
    path_a: Annotated[str | None, Field(description="First PDF path for compare operation.")] = None,
    path_b: Annotated[str | None, Field(description="Second PDF path for compare operation.")] = None,
) -> dict:
    """Audit PDF quality and compliance.

    PDF/A, structure, accessibility, integrity, and comparison checks.

    ## Return Format

    A dict with keys:
    - success: bool - whether the operation succeeded
    - message: str - human-readable summary
    - operation-specific keys:
      - pdfa: {is_pdfa, details}
      - structure: {has_tags, headings, paragraphs, issues}
      - accessibility: {score (0-100), issues}
      - integrity: {intact, pages_readable, warnings}
      - compare: {same_page_count, text_similarity, diffs}
    On failure: {success: False, error, error_type}.

    ## Examples

    >>> await pdf_validate(operation="accessibility", path="report.pdf")
    {"success": true, "score": 75, "issues": [...],
     "message": "Accessibility score: 75/100 for report.pdf. 0 errors, 1 warnings."}

    >>> await pdf_validate(operation="compare", path_a="a.pdf", path_b="b.pdf")
    {"success": true, "same_page_count": true, "text_similarity": 0.98, "diffs": [],
     "message": "Comparison: same page count, 98.0% text similarity between a.pdf and b.pdf."}
    """
    try:
        if operation == "pdfa":
            doc = fitz.open(path)
            try:
                metadata = doc.metadata
                is_pdfa = False
                details = {}
                if metadata:
                    fmt = metadata.get("format", "")
                    is_pdfa = "pdf/a" in fmt.lower() if fmt else False
                    details = {
                        "format": fmt,
                        "title": metadata.get("title"),
                        "subject": metadata.get("subject"),
                        "creator": metadata.get("creator"),
                    }
                pages_ok = 0
                for i in range(len(doc)):
                    try:
                        _ = doc[i].get_text()
                        pages_ok += 1
                    except Exception:
                        pass
                details["pages_readable"] = pages_ok
                return {
                    "success": True,
                    "is_pdfa": is_pdfa,
                    "details": details,
                    "message": f"PDF/A check: {'compliant' if is_pdfa else 'not compliant'} for {Path(path).name}.",
                }
            finally:
                doc.close()

        elif operation == "structure":
            doc = fitz.open(path)
            try:
                has_tags = doc.get_toc() is not None
                total_headings = 0
                total_paragraphs = 0
                issues = []
                for i in range(len(doc)):
                    page = doc[i]
                    text = str(page.get_text())
                    blocks = cast(list[Any], page.get_text("blocks"))
                    for block in blocks:
                        block_text = block[4].strip() if len(block) > 4 else ""
                        if block_text and len(block_text) < 100 and any(c.isupper() for c in block_text[:20]) and block_text[-1] not in ".!?":
                            total_headings += 1
                        elif block_text and len(block_text) > 50:
                            total_paragraphs += 1
                    if not text.strip():
                        issues.append(f"Page {i + 1} appears to have no text content.")
                return {
                    "success": True,
                    "has_tags": has_tags,
                    "headings": total_headings,
                    "paragraphs": total_paragraphs,
                    "issues": issues,
                    "message": f"Structure check: {total_headings} headings, {total_paragraphs} paragraphs, {len(issues)} issues in {Path(path).name}.",
                }
            finally:
                doc.close()

        elif operation == "accessibility":
            doc = fitz.open(path)
            try:
                issues = []
                score = 100
                metadata = doc.metadata
                lang = (metadata.get("language") or "") if metadata else ""
                if not lang:
                    issues.append({"type": "language", "severity": "error", "message": "Document language not set."})
                    score -= 20
                else:
                    issues.append({"type": "language", "severity": "info", "message": f"Language set to {lang}."})
                has_tags = doc.get_toc() is not None
                if not has_tags:
                    issues.append(
                        {
                            "type": "tags",
                            "severity": "warning",
                            "message": "Document has no tagged content structure / TOC.",
                        }
                    )
                    score -= 15
                alt_text_count = 0
                for i in range(len(doc)):
                    page = doc[i]
                    for img in page.get_images():
                        alt_text_count += 1
                if alt_text_count == 0:
                    issues.append({"type": "images", "severity": "info", "message": "No images found (no alt-text check needed)."})
                else:
                    issues.append(
                        {
                            "type": "images",
                            "severity": "info",
                            "message": f"Found {alt_text_count} images — alt-text check recommended.",
                        }
                    )
                if not doc.get_toc():
                    issues.append(
                        {
                            "type": "headings",
                            "severity": "warning",
                            "message": "No heading structure detected (TOC is empty).",
                        }
                    )
                    score -= 10
                score = max(0, score)
                return {
                    "success": True,
                    "score": score,
                    "issues": issues,
                    "message": f"Accessibility score: {score}/100 for {Path(path).name}. "
                    f"{len([x for x in issues if 'error' in x.get('severity', '')])} errors, "
                    f"{len([x for x in issues if 'warning' in x.get('severity', '')])} warnings.",
                }
            finally:
                doc.close()

        elif operation == "integrity":
            doc = fitz.open(path)
            try:
                warnings = []
                pages_ok = 0
                for i in range(len(doc)):
                    try:
                        page = doc[i]
                        _ = page.get_text()
                        _ = page.rect
                        pages_ok += 1
                    except Exception as page_err:
                        warnings.append(f"Page {i + 1}: {page_err}")
                intact = pages_ok == len(doc)
                if not intact:
                    warnings.append(f"Only {pages_ok}/{len(doc)} pages fully readable.")
                return {
                    "success": True,
                    "intact": intact,
                    "pages_readable": pages_ok,
                    "warnings": warnings,
                    "message": f"Integrity check: {'intact' if intact else 'corrupted'} — {pages_ok}/{len(doc)} pages readable in {Path(path).name}.",
                }
            finally:
                doc.close()

        elif operation == "compare":
            if not path_a or not path_b:
                return {"success": False, "error": "path_a and path_b are required for compare."}
            text_a = _get_text(path_a)
            text_b = _get_text(path_b)
            count_a = _page_count(path_a)
            count_b = _page_count(path_b)
            same_count = count_a == count_b
            ratio = difflib.SequenceMatcher(None, text_a, text_b).ratio()
            diffs = []
            if not same_count:
                diffs.append(f"Page count differs: {count_a} vs {count_b}.")
            if ratio < 1.0:
                diff_lines = list(difflib.unified_diff(text_a.splitlines(True), text_b.splitlines(True), n=0))
                diffs.extend(diff_lines[:10])
                if len(diff_lines) > 10:
                    diffs.append(f"... and {len(diff_lines) - 10} more differences.")
            return {
                "success": True,
                "same_page_count": same_count,
                "text_similarity": round(ratio, 4),
                "diffs": diffs,
                "message": f"Comparison: {'same' if same_count else 'different'} page count, {ratio:.1%} text similarity between {Path(path_a).name} and {Path(path_b).name}.",
            }
    except Exception as e:
        logger.exception("pdf_validate %s failed: %s", operation, e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
