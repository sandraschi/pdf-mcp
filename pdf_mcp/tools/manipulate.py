import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from mcp.types import ToolAnnotations
from pydantic import Field

from pdf_mcp.config import cfg
from pdf_mcp.models import PdfManipulateOperation
from pdf_mcp.server import mcp
from pdf_mcp.services.manipulator import Manipulator

logger = logging.getLogger("pdf-mcp")
manipulator = Manipulator()


def _out_path(path: str, op: str) -> str:
    p = Path(path)
    cfg.upload_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    return str(cfg.upload_dir / f"{p.stem}_{op}_{ts}_{uid}.pdf")


def _merge_out_path(paths: list[str], op: str) -> str:
    cfg.upload_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    stem = Path(paths[0]).stem if paths else "merged"
    return str(cfg.upload_dir / f"{stem}_{op}_{ts}_{uid}.pdf")


def _parse_page_range(s: str) -> list[int]:
    pages = set()
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.update(range(int(start.strip()) - 1, int(end.strip())))
        else:
            pages.add(int(part) - 1)
    return sorted(pages)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True))
async def pdf_manipulate(
    operation: PdfManipulateOperation,
    path: Annotated[str, Field(description="Path to the PDF file. Ignored for merge.")],
    paths: Annotated[list[str] | None, Field(description="List of PDF paths to merge. Only for merge operation.")] = None,
    output_path: Annotated[str | None, Field(description="Output path. Auto-generated if omitted.")] = None,
    pages: Annotated[str | None, Field(description="Page range string (e.g. '1-5,7,9-12'). For rotate operation.")] = None,
    angle: Annotated[int, Field(description="Rotation angle in degrees. Default 90.")] = 90,
    new_order: Annotated[list[int] | None, Field(description="New page order (1-indexed list). For reorder operation.")] = None,
    page_list: Annotated[list[int] | None, Field(description="List of page numbers to delete. For delete_pages operation.")] = None,
    quality: Annotated[int, Field(description="Compression quality 1-100. Default 85.")] = 85,
    password: Annotated[str | None, Field(description="Password for encrypt/decrypt operations.")] = None,
    output_dir: Annotated[str | None, Field(description="Output directory for split operation.")] = None,
    ranges: Annotated[list[list[int]] | None, Field(description="Split ranges as list of [start, end] pairs (1-indexed).")] = None,
) -> dict:
    """Modify PDF structure and properties.

    Merge, split, rotate, reorder, delete pages, compress, encrypt/decrypt, and optimize PDFs.

    ## Return Format

    A dict with keys:
    - success: bool - whether the operation succeeded
    - message: str - human-readable summary
    - operation-specific keys:
      - merge: {path, pages}
      - split: {files: [path, ...]}
      - rotate/reorder/delete_pages/encrypt/decrypt: {path}
      - compress: {path, original_size, compressed_size}
      - optimize: {path, original_size, optimized_size}
    On failure: {success: False, error, error_type}.

    ## Examples

    >>> await pdf_manipulate(operation="merge", path="a.pdf", paths=["a.pdf", "b.pdf"])
    {"success": true, "path": ".../merged_....pdf", "pages": 4,
     "message": "Merged 2 PDFs into merged_....pdf (4 pages)."}

    >>> await pdf_manipulate(operation="rotate", path="report.pdf", angle=90)
    {"success": true, "path": ".../report_rotate_....pdf",
     "message": "Rotated report.pdf by 90 degrees, saved to report_rotate_....pdf."}
    """
    try:
        if operation == "merge":
            result = manipulator.merge(paths or [], output_path or _merge_out_path(paths or [], "merge"))
            return {
                "success": True,
                "path": result["path"],
                "pages": result["pages"],
                "message": f"Merged {len(paths or [])} PDFs into {Path(result['path']).name} ({result['pages']} pages).",
            }
        elif operation == "split":
            result = manipulator.split(path, output_dir=output_dir or str(cfg.upload_dir / "split"), ranges=ranges)
            return {
                "success": True,
                "files": result["files"],
                "message": f"Split {Path(path).name} into {len(result['files'])} files.",
            }
        elif operation == "rotate":
            op = output_path or _out_path(path, "rotate")
            page_range = _parse_page_range(pages) if pages else None
            result = manipulator.rotate(path, output_path=op, pages=page_range, angle=angle)
            return {
                "success": True,
                "path": result["path"],
                "message": f"Rotated {Path(path).name} by {angle} degrees, saved to {Path(result['path']).name}.",
            }
        elif operation == "reorder":
            op = output_path or _out_path(path, "reorder")
            result = manipulator.reorder(path, output_path=op, new_order=new_order or [])
            return {
                "success": True,
                "path": result["path"],
                "message": f"Reordered pages of {Path(path).name}, saved to {Path(result['path']).name}.",
            }
        elif operation == "delete_pages":
            op = output_path or _out_path(path, "delete")
            result = manipulator.delete_pages(path, output_path=op, pages=page_list or [])
            return {
                "success": True,
                "path": result["path"],
                "message": f"Deleted {len(page_list or [])} pages from {Path(path).name}, saved to {Path(result['path']).name}.",
            }
        elif operation == "compress":
            op = output_path or _out_path(path, "compress")
            result = manipulator.compress(path, output_path=op, quality=quality)
            return {
                "success": True,
                "path": result["path"],
                "original_size": result["original_size"],
                "compressed_size": result["compressed_size"],
                "message": f"Compressed {Path(path).name} from {_fmt_size(result['original_size'])} to {_fmt_size(result['compressed_size'])}.",
            }
        elif operation == "encrypt":
            op = output_path or _out_path(path, "encrypt")
            result = manipulator.encrypt(path, output_path=op, password=password or "")
            return {
                "success": True,
                "path": result["path"],
                "message": f"Encrypted {Path(path).name} with password, saved to {Path(result['path']).name}.",
            }
        elif operation == "decrypt":
            op = output_path or _out_path(path, "decrypt")
            result = manipulator.decrypt(path, output_path=op, password=password or "")
            return {
                "success": True,
                "path": result["path"],
                "message": f"Decrypted {Path(path).name}, saved to {Path(result['path']).name}.",
            }
        elif operation == "optimize":
            op = output_path or _out_path(path, "optimize")
            result = manipulator.optimize(path, output_path=op)
            return {
                "success": True,
                "path": result["path"],
                "original_size": result["original_size"],
                "optimized_size": result["optimized_size"],
                "message": f"Optimized {Path(path).name} from {_fmt_size(result['original_size'])} to {_fmt_size(result['optimized_size'])}.",
            }
    except Exception as e:
        logger.exception("pdf_manipulate %s failed: %s", operation, e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


def _fmt_size(b: int) -> str:
    if b < 1024:
        return f"{b}B"
    elif b < 1048576:
        return f"{b / 1024:.1f}KB"
    return f"{b / 1048576:.1f}MB"
