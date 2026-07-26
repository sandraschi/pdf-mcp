import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import fitz
from pydantic import Field

from pdf_mcp.config import cfg
from pdf_mcp.models import PdfFormsOperation
from pdf_mcp.server import mcp

logger = logging.getLogger("pdf-mcp")


def _out_path(path: str, op: str) -> str:
    p = Path(path)
    cfg.upload_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    return str(cfg.upload_dir / f"{p.stem}_{op}_{ts}_{uid}.pdf")


def _get_widgets(page) -> list:
    try:
        return list(page.widgets())
    except Exception:
        return []


@mcp.tool()
async def pdf_forms(
    operation: PdfFormsOperation,
    path: Annotated[str, Field(description="Path to the PDF file.")],
    output_path: Annotated[str | None, Field(description="Output path. Auto-generated if omitted.")] = None,
    fields: Annotated[dict | None, Field(description="Dict of field_name: value for fill operation.")] = None,
) -> dict:
    try:
        if operation == "list_fields":
            doc = fitz.open(path)
            try:
                result = []
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    for widget in _get_widgets(page):
                        result.append(
                            {
                                "name": widget.field_name,
                                "type": widget.field_type_string,
                                "value": widget.field_value,
                                "page": page_num,
                                "rect": [widget.rect.x0, widget.rect.y0, widget.rect.x1, widget.rect.y1],
                            }
                        )
                return {
                    "success": True,
                    "fields": result,
                    "message": f"Found {len(result)} form fields in {Path(path).name}.",
                }
            finally:
                doc.close()

        elif operation == "fill":
            op = output_path or _out_path(path, "fill")
            doc = fitz.open(path)
            try:
                filled = 0
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    for widget in _get_widgets(page):
                        name = widget.field_name
                        if name in (fields or {}):
                            widget.field_value = str(fields[name])
                            widget.update()
                            filled += 1
                doc.save(op, garbage=4, deflate=True)
                return {
                    "success": True,
                    "path": op,
                    "message": f"Filled {filled} form fields in {Path(path).name}, saved to {Path(op).name}.",
                }
            finally:
                doc.close()

        elif operation == "flatten":
            op = output_path or _out_path(path, "flatten")
            doc = fitz.open(path)
            try:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    for widget in _get_widgets(page):
                        widget.field_flags = widget.field_flags | 1
                        widget.update()
                doc.save(op, garbage=4, deflate=True)
                return {
                    "success": True,
                    "path": op,
                    "message": f"Flattened form fields in {Path(path).name}, saved to {Path(op).name}.",
                }
            finally:
                doc.close()

        elif operation == "export_data":
            doc = fitz.open(path)
            try:
                data = {}
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    for widget in _get_widgets(page):
                        data[widget.field_name] = widget.field_value
                return {
                    "success": True,
                    "data": data,
                    "message": f"Exported {len(data)} form field values from {Path(path).name}.",
                }
            finally:
                doc.close()
    except Exception as e:
        logger.exception("pdf_forms %s failed: %s", operation, e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
