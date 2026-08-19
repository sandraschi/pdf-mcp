import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from mcp.types import ToolAnnotations
from pydantic import Field

from pdf_mcp.config import cfg
from pdf_mcp.models import PdfExtractOperation
from pdf_mcp.server import mcp
from pdf_mcp.services.extractor import Extractor

logger = logging.getLogger("pdf-mcp")
extractor = Extractor()


def _parse_page_range(s: str | None) -> list[int] | None:
    if not s:
        return None
    pages = set()
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.update(range(int(start.strip()) - 1, int(end.strip())))
        else:
            pages.add(int(part) - 1)
    return sorted(pages)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def pdf_extract(
    operation: PdfExtractOperation,
    path: Annotated[str, Field(description="Path to the PDF file.")],
    pages: Annotated[str | None, Field(description="Optional page range (e.g. '1-5,7,9-12'). All pages if omitted.")] = None,
) -> dict:
    """Extract content and metadata from a PDF.

    Supports text, images, tables, metadata, fonts, links, and outline extraction
    through a single portmanteau tool.

    Args are validated and documented via Annotated fields on the signature.

    ## Return Format

    A dict with keys:
    - success: bool - whether the operation succeeded
    - message: str - human-readable summary
    - operation-specific keys:
      - text: {text, pages, page_count}
      - images: {images: [{page, index, width, height, path, ext}]}
      - tables: {tables: [{page, rows, cols, headers, data}]}
      - metadata: {metadata: {...}}
      - fonts: {fonts: [{name, type, encoding, embedded, size}]}
      - links: {links: [{page, uri, page_target, rect}]}
      - outline: {outline: [{title, level, page, children}]}
    On failure: {success: False, error, error_type}.

    ## Examples

    >>> await pdf_extract(operation="text", path="report.pdf", pages="1-3")
    {"success": true, "text": "...", "pages": 3, "page_count": 12,
     "message": "Extracted 3 pages of text from report.pdf."}

    >>> await pdf_extract(operation="metadata", path="report.pdf")
    {"success": true, "metadata": {"title": "Report", ...},
     "message": "Extracted metadata from report.pdf."}
    """
    try:
        page_list = _parse_page_range(pages)
        if operation == "text":
            result = extractor.extract_text(path, page_nums=page_list)
            if not result.get("success"):
                return result
            return {
                "success": True,
                "text": result["text"],
                "pages": result["pages"],
                "page_count": result["page_count"],
                "message": f"Extracted {result['pages']} pages of text from {Path(path).name}.",
            }
        elif operation == "images":
            img_dir = str(cfg.upload_dir / f"{Path(path).stem}_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}")
            result = extractor.extract_images(path, output_dir=img_dir, page_nums=page_list)
            if not result.get("success"):
                return result
            return {
                "success": True,
                "images": result["images"],
                "message": f"Extracted {len(result['images'])} images from {Path(path).name}.",
            }
        elif operation == "tables":
            result = extractor.extract_tables(path, page_nums=page_list)
            if not result.get("success"):
                return result
            return {
                "success": True,
                "tables": result["tables"],
                "message": f"Extracted {len(result['tables'])} tables from {Path(path).name}.",
            }
        elif operation == "metadata":
            result = extractor.extract_metadata(path)
            if not result.get("success"):
                return result
            return {
                "success": True,
                "metadata": result["metadata"],
                "message": f"Extracted metadata from {Path(path).name}.",
            }
        elif operation == "fonts":
            result = extractor.extract_fonts(path)
            if not result.get("success"):
                return result
            return {
                "success": True,
                "fonts": result["fonts"],
                "message": f"Found {len(result['fonts'])} fonts in {Path(path).name}.",
            }
        elif operation == "links":
            result = extractor.extract_links(path)
            if not result.get("success"):
                return result
            return {
                "success": True,
                "links": result["links"],
                "message": f"Extracted {len(result['links'])} links from {Path(path).name}.",
            }
        elif operation == "outline":
            result = extractor.extract_outline(path)
            if not result.get("success"):
                return result
            return {
                "success": True,
                "outline": result["outline"],
                "message": f"Extracted outline from {Path(path).name}.",
            }
        return {"success": False, "error": f"Unknown operation: {operation}"}
    except Exception as e:
        logger.exception("pdf_extract %s failed: %s", operation, e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
