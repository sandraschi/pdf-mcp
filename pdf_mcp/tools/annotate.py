import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import fitz
from pydantic import Field

from pdf_mcp.config import cfg
from pdf_mcp.models import PdfAnnotateOperation
from pdf_mcp.server import mcp

logger = logging.getLogger("pdf-mcp")


def _out_path(path: str, op: str) -> str:
    p = Path(path)
    cfg.upload_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    return str(cfg.upload_dir / f"{p.stem}_{op}_{ts}_{uid}.pdf")


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


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


@mcp.tool()
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
    try:
        op = output_path or _out_path(path, operation)

        if operation in ("watermark",):
            doc = fitz.open(path)
            try:
                for i, page in enumerate(doc):
                    rect = page.rect
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
                        page.insert_image(img_rect, filename=image_path, overlay=True, rotate=0)
                    elif text:
                        pts = _watermark_position(rect, position, text, 24)
                        for px, py in pts:
                            annot = page.add_stamp_annot(fitz.Rect(px, py, px + 200, py + 30), stamp=0)
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
            doc = fitz.open(path)
            try:
                for i, p in enumerate(doc):
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
    except Exception as e:
        logger.exception("pdf_annotate %s failed: %s", operation, e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
