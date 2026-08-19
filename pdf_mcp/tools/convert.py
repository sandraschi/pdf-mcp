import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from mcp.types import ToolAnnotations
from pydantic import Field

from pdf_mcp.config import cfg
from pdf_mcp.models import PdfConvertOperation
from pdf_mcp.server import mcp
from pdf_mcp.services.converter import Converter

logger = logging.getLogger("pdf-mcp")
converter = Converter()


def _out_path(path: str, op: str, ext: str = ".pdf") -> str:
    p = Path(path)
    cfg.upload_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    return str(cfg.upload_dir / f"{p.stem}_{op}_{ts}_{uid}{ext}")


def _out_path_no_input(op: str, ext: str = ".pdf") -> str:
    cfg.upload_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    return str(cfg.upload_dir / f"output_{op}_{ts}_{uid}{ext}")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True))
async def pdf_convert(
    operation: PdfConvertOperation,
    path: Annotated[str | None, Field(description="Path to the PDF file. Required for to_* operations.")] = None,
    output_path: Annotated[str | None, Field(description="Output path. Auto-generated if omitted.")] = None,
    output_dir: Annotated[str | None, Field(description="Output directory for to_images operation.")] = None,
    fmt: Annotated[str, Field(description="Image format (png, jpeg). Default png.")] = "png",
    dpi: Annotated[int, Field(description="DPI for image output. Default 200.")] = 200,
    html: Annotated[str | None, Field(description="HTML content for from_html operation.")] = None,
    markdown: Annotated[str | None, Field(description="Markdown content for from_markdown operation.")] = None,
    paths: Annotated[list[str] | None, Field(description="Image paths for from_images operation.")] = None,
) -> dict:
    """Convert between PDF and other formats.

    PDF to/from Markdown, HTML, and images.

    ## Return Format

    A dict with keys:
    - success: bool - whether the operation succeeded
    - message: str - human-readable summary
    - operation-specific keys:
      - to_markdown: {markdown, pages}
      - to_images: {images: [{page, path, width, height}]}
      - to_html: {html}
      - from_html/from_markdown/from_images: {path, pages}
    On failure: {success: False, error, error_type}.

    ## Examples

    >>> await pdf_convert(operation="to_markdown", path="report.pdf")
    {"success": true, "markdown": "# Report...", "pages": 3,
     "message": "Converted report.pdf to markdown (3 pages)."}

    >>> await pdf_convert(operation="from_markdown", markdown="# Hello")
    {"success": true, "path": ".../output_from_markdown_....pdf", "pages": 1,
     "message": "Created PDF from markdown (1 pages), saved to output_from_markdown_....pdf."}
    """
    try:
        if operation == "to_markdown":
            if not path:
                return {"success": False, "error": "path is required for to_markdown."}
            result = converter.to_markdown(path)
            return {
                "success": True,
                "markdown": result["markdown"],
                "pages": result["pages"],
                "message": f"Converted {Path(path).name} to markdown ({result['pages']} pages).",
            }

        elif operation == "to_images":
            if not path:
                return {"success": False, "error": "path is required for to_images."}
            img_dir = output_dir or str(cfg.upload_dir / f"{Path(path).stem}_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}")
            Path(img_dir).mkdir(parents=True, exist_ok=True)
            result = converter.to_images(path, output_dir=img_dir, fmt=fmt, dpi=dpi)
            return {
                "success": True,
                "images": result["images"],
                "message": f"Converted {Path(path).name} to {len(result['images'])} {fmt} images.",
            }

        elif operation == "to_html":
            if not path:
                return {"success": False, "error": "path is required for to_html."}
            result = converter.to_html(path)
            return {"success": True, "html": result["html"], "message": f"Converted {Path(path).name} to HTML."}

        elif operation == "from_html":
            op = output_path or _out_path_no_input("from_html")
            result = converter.from_html(html or "", output_path=op)
            return {
                "success": True,
                "path": result["path"],
                "pages": result["pages"],
                "message": f"Created PDF from HTML ({result['pages']} pages), saved to {Path(result['path']).name}.",
            }

        elif operation == "from_markdown":
            op = output_path or _out_path_no_input("from_markdown")
            result = converter.from_markdown(markdown or "", output_path=op)
            return {
                "success": True,
                "path": result["path"],
                "pages": result["pages"],
                "message": f"Created PDF from markdown ({result['pages']} pages), saved to {Path(result['path']).name}.",
            }

        elif operation == "from_images":
            op = output_path or _out_path_no_input("from_images")
            result = converter.from_images(paths or [], output_path=op)
            return {
                "success": True,
                "path": result["path"],
                "pages": result["pages"],
                "message": f"Created PDF from {len(paths or [])} images ({result['pages']} pages), saved to {Path(result['path']).name}.",
            }
    except Exception as e:
        logger.exception("pdf_convert %s failed: %s", operation, e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
