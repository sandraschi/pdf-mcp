import logging
from pathlib import Path
from typing import Annotated

from pydantic import Field

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


@mcp.tool()
async def pdf_extract(
    operation: PdfExtractOperation,
    path: Annotated[str, Field(description="Path to the PDF file.")],
    pages: Annotated[str | None, Field(description="Optional page range (e.g. '1-5,7,9-12'). All pages if omitted.")] = None,
) -> dict:
    try:
        page_list = _parse_page_range(pages)
        if operation == "text":
            result = extractor.extract_text(path, pages=page_list)
            return {
                "success": True,
                "text": result["text"],
                "pages": result["pages"],
                "page_count": result["page_count"],
                "message": f"Extracted {result['pages']} pages of text from {Path(path).name}.",
            }
        elif operation == "images":
            result = extractor.extract_images(path, pages=page_list)
            return {
                "success": True,
                "images": result["images"],
                "message": f"Extracted {len(result['images'])} images from {Path(path).name}.",
            }
        elif operation == "tables":
            result = extractor.extract_tables(path, pages=page_list)
            return {
                "success": True,
                "tables": result["tables"],
                "message": f"Extracted {len(result['tables'])} tables from {Path(path).name}.",
            }
        elif operation == "metadata":
            result = extractor.extract_metadata(path)
            return {
                "success": True,
                "metadata": result["metadata"],
                "message": f"Extracted metadata from {Path(path).name}.",
            }
        elif operation == "fonts":
            result = extractor.extract_fonts(path)
            return {
                "success": True,
                "fonts": result["fonts"],
                "message": f"Found {len(result['fonts'])} fonts in {Path(path).name}.",
            }
        elif operation == "links":
            result = extractor.extract_links(path)
            return {
                "success": True,
                "links": result["links"],
                "message": f"Extracted {len(result['links'])} links from {Path(path).name}.",
            }
        elif operation == "outline":
            result = extractor.extract_outline(path)
            return {
                "success": True,
                "outline": result["outline"],
                "message": f"Extracted outline from {Path(path).name}.",
            }
    except Exception as e:
        logger.exception("pdf_extract %s failed: %s", operation, e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
