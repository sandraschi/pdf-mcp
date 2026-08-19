import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import fitz
from mcp.types import ToolAnnotations
from pydantic import Field

from pdf_mcp.config import cfg
from pdf_mcp.models import PdfAnnotateOperation
from pdf_mcp.server import mcp
from pdf_mcp.tools._schema import TOOL_OUTPUT_SCHEMA

logger = logging.getLogger("pdf-mcp")


def _out_path(path: str, op: str) -> str:
    p = Path(path)
    cfg.upload_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    return str(cfg.upload_dir / f"{p.stem}_{op}_{ts}_{uid}.pdf")


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (r, g, b)


def _watermark_position(rect: fitz.Rect, position: str, text: str, font_size: int) -> list[tuple[float, float]]:
    tw = font_size * len(text) * 0.5
    pw, ph = rect.width, rect.height
    if position == "tile":
        positions = []
        for y in range(50, int(ph), 120):
            for x in range(20, int(pw), int(tw) + 40):
                positions.append((float(x), float(y)))
        return positions
    pos_map = {
        "top_left": (10, 10),
        "top_right": (pw - tw - 10, 10),
        "bottom_left": (10, ph - 20),
        "bottom_right": (pw - tw - 10, ph - 20),
        "center": (pw / 2 - tw / 2, ph / 2),
    }
    return [pos_map.get(position, (pw / 2 - tw / 2, ph / 2))]


@mcp.tool(output_schema=TOOL_OUTPUT_SCHEMA, annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True))
async def pdf_annotate(
    operation: PdfAnnotateOperation,
    path: Annotated[str, Field(description="Path to the PDF file.")],
    output_path: Annotated[str | None, Field(description="Output path. Auto-generated if omitted.")] = None,
    text: Annotated[str | None, Field(description="Text content for watermark, stamp, header, or footer.")] = None,
    image_path: Annotated[str | None, Field(description="Path to image file for image watermark.")] = None,
    opacity: Annotated[float, Field(description="Opacity for watermark. Default 0.3.")] = 0.3,
    position: Annotated[str, Field(description="Watermark position: center, top_left, top_right, bottom_left, bottom_right, tile.")] = "center",
    page: Annotated[int | None, Field(description="Target page number (1-indexed). Applies to all pages if omitted.")] = None,
    x: Annotated[int, Field(description="X position for stamp annotation. Default 50.")] = 50,
    y: Annotated[int, Field(description="Y position for stamp annotation. Default 50.")] = 50,
    search_text: Annotated[str | None, Field(description="Text to search for highlighting or underlining.")] = None,
    color: Annotated[str, Field(description="Highlight color as hex. Default #FFFF00.")] = "#FFFF00",
    header: Annotated[str | None, Field(description="Header text.")] = None,
    footer: Annotated[str | None, Field(description="Footer text.")] = None,
    font_size: Annotated[int, Field(description="Font size for header/footer/page numbers. Default 10.")] = 10,
    start: Annotated[int, Field(description="Starting page number. Default 1.")] = 1,
) -> dict:
    """Add annotations and markup to PDFs.

    Watermark, stamp, highlight, underline, header/footer, and page numbers.

    ## Return Format

    A dict with keys:
    - success: bool - whether the operation succeeded
    - message: str - human-readable summary
    - operation-specific keys:
      - watermark/stamp/header_footer/page_numbers: {path}
      - highlight: {path, occurrences}
      - underline: {path, occurrences}
    On failure: {success: False, error, error_type}.

    ## Examples

    >>> await pdf_annotate(operation="watermark", path="report.pdf", text="CONFIDENTIAL", opacity=0.3)
    {"success": true, "path": ".../report_watermark_....pdf",
     "message": "Added watermark to report.pdf, saved to report_watermark_....pdf."}

    >>> await pdf_annotate(operation="highlight", path="report.pdf", search_text="revenue")
    {"success": true, "path": ".../report_highlight_....pdf", "occurrences": 3,
     "message": "Highlighted 3 occurrences of 'revenue' in report.pdf."}
    """
    try:
        op = output_path or _out_path(path, operation)

        if operation in ("watermark",):
            doc: fitz.Document = fitz.open(path)
            try:
                for i in range(len(doc)):
                    pg = doc[i]
                    rect = pg.rect
                    if image_path:
                        img_rect = fitz.Rect(0, 0, rect.width * 0.3, rect.height * 0.3)
                        if position == "center":
                            img_rect = img_rect + (
                                rect.width / 2 - img_rect.width / 2,
                                rect.height / 2 - img_rect.height / 2,
                            )
                        elif position == "top_left":
                            pass
                        elif position == "top_right":
                            img_rect = img_rect + (rect.width - img_rect.width, 0)
                        elif position == "bottom_left":
                            img_rect = img_rect + (0, rect.height - img_rect.height)
                        elif position == "bottom_right":
                            img_rect = img_rect + (rect.width - img_rect.width, rect.height - img_rect.height)
                        pg.insert_image(img_rect, filename=image_path, overlay=True, rotate=0)
                    elif text:
                        pts = _watermark_position(rect, position, text, 24)
                        for px, py in pts:
                            annot = pg.add_stamp_annot(fitz.Rect(px, py, px + 200, py + 30), stamp=0)
                            annot.set_info(info=text)
                            annot.update(opacity=opacity)
                doc.save(op, garbage=4, deflate=True)
                return {
                    "success": True,
                    "path": op,
                    "message": f"Added watermark to {Path(path).name}, saved to {Path(op).name}.",
                }
            finally:
                doc.close()

        elif operation == "stamp":
            doc = fitz.open(path)
            try:
                pages_to_process = [page - 1 for page in ([page] if page else range(len(doc)))]
                for i in pages_to_process:
                    p = doc[i]
                    annot = p.add_stamp_annot(fitz.Rect(x, y, x + 200, y + 30), stamp=0)
                    annot.set_info(info=text or "")
                    annot.update()
                doc.save(op, garbage=4, deflate=True)
                return {
                    "success": True,
                    "path": op,
                    "message": f"Added stamp to {Path(path).name}, saved to {Path(op).name}.",
                }
            finally:
                doc.close()

        elif operation == "highlight":
            doc = fitz.open(path)
            try:
                rgb = _hex_to_rgb(color)
                pages_to_process = [page - 1 for page in ([page] if page else range(len(doc)))]
                found = 0
                for i in pages_to_process:
                    p = doc[i]
                    areas = p.search_for(search_text or "")
                    for area in areas:
                        annot = p.add_highlight_annot(area)
                        annot.set_colors(stroke=rgb)
                        annot.update()
                        found += 1
                doc.save(op, garbage=4, deflate=True)
                return {
                    "success": True,
                    "path": op,
                    "message": f"Highlighted {found} occurrences of '{search_text}' in {Path(path).name}.",
                }
            finally:
                doc.close()

        elif operation == "underline":
            doc = fitz.open(path)
            try:
                pages_to_process = [page - 1 for page in ([page] if page else range(len(doc)))]
                found = 0
                for i in pages_to_process:
                    p = doc[i]
                    areas = p.search_for(search_text or "")
                    for area in areas:
                        annot = p.add_underline_annot(area)
                        annot.update()
                        found += 1
                doc.save(op, garbage=4, deflate=True)
                return {
                    "success": True,
                    "path": op,
                    "message": f"Underlined {found} occurrences of '{search_text}' in {Path(path).name}.",
                }
            finally:
                doc.close()

        elif operation == "header_footer":
            doc = fitz.open(path)
            try:
                for p in doc:
                    rect = p.rect
                    if header:
                        p.insert_text(fitz.Point(rect.x0 + 50, rect.y0 + 20), header, fontsize=font_size, color=(0.3, 0.3, 0.3))
                    if footer:
                        p.insert_text(fitz.Point(rect.x0 + 50, rect.y1 - 15), footer, fontsize=font_size, color=(0.3, 0.3, 0.3))
                doc.save(op, garbage=4, deflate=True)
                return {
                    "success": True,
                    "path": op,
                    "message": f"Added header/footer to {Path(path).name}, saved to {Path(op).name}.",
                }
            finally:
                doc.close()

        elif operation == "page_numbers":
            doc: fitz.Document = fitz.open(path)
            try:
                for i in range(len(doc)):
                    p = doc[i]
                    num = start + i
                    rect = p.rect
                    if position == "bottom_center":
                        px, py = rect.width / 2 - 10, rect.y1 - 20
                    elif position == "bottom_right":
                        px, py = rect.x1 - 40, rect.y1 - 20
                    elif position == "top_center":
                        px, py = rect.width / 2 - 10, rect.y0 + 15
                    elif position == "top_right":
                        px, py = rect.x1 - 40, rect.y0 + 15
                    else:
                        px, py = rect.width / 2 - 10, rect.y1 - 20
                    p.insert_text(fitz.Point(px, py), str(num), fontsize=font_size, color=(0.3, 0.3, 0.3))
                doc.save(op, garbage=4, deflate=True)
                return {
                    "success": True,
                    "path": op,
                    "message": f"Added page numbers to {Path(path).name}, saved to {Path(op).name}.",
                }
            finally:
                doc.close()

        elif operation == "summary_box":
            try:
                from pdf_mcp.services.llm import chat_completion

                doc: fitz.Document = fitz.open(path)
                try:
                    doc_text = " ".join(str(doc[i].get_text()) for i in range(min(len(doc), 10)))
                finally:
                    doc.close()
                summary = await chat_completion(
                    [
                        {"role": "system", "content": "Write a 2-3 sentence factual summary of the document."},
                        {"role": "user", "content": doc_text[:6000]},
                    ]
                )
            except Exception as e:
                logger.exception("pdf_annotate summary_box LLM failed: %s", e)
                return {"success": False, "error": f"summary_box requires a local LLM: {e}"}
            doc: fitz.Document = fitz.open(path)
            try:
                first = doc[0]
                rect = first.rect
                y = rect.y0 + 15
                for line in summary.splitlines():
                    if not line.strip():
                        continue
                    if y > rect.y0 + 220:
                        break
                    first.insert_text(fitz.Point(rect.x0 + 50, y), line.strip(), fontsize=10, color=(0.1, 0.1, 0.1))
                    y += 16
                doc.save(op, garbage=4, deflate=True)
                return {
                    "success": True,
                    "path": op,
                    "summary": summary,
                    "message": f"Added summary box to page 1 of {Path(path).name}, saved to {Path(op).name}.",
                }
            finally:
                doc.close()
    except Exception as e:
        logger.exception("pdf_annotate %s failed: %s", operation, e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
