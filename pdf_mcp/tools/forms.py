import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import fitz
from mcp.types import ToolAnnotations
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


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def pdf_forms(
    operation: PdfFormsOperation,
    path: Annotated[str, Field(description="Path to the PDF file.")],
    output_path: Annotated[str | None, Field(description="Output path. Auto-generated if omitted.")] = None,
    fields: Annotated[dict | None, Field(description="Dict of field_name: value for fill operation.")] = None,
    source: Annotated[str | None, Field(description="Source PDF path whose text drives auto_fill.")] = None,
    text: Annotated[str | None, Field(description="Source text driving auto_fill (alternative to source).")] = None,
) -> dict:
    """Handle interactive form fields.

    List, fill, flatten, export, and auto-fill (LLM-guided) PDF form fields.

    ## Return Format

    A dict with keys:
    - success: bool
    - message: str - human-readable summary
    - operation-specific keys:
      - list_fields: {fields: [{name, type, value, page, rect}]}
      - fill/flatten: {path}
      - export_data: {data: {field_name: value}}
      - auto_fill: {path, filled, missing}
    On failure: {success: False, error, error_type}.

    ## Examples

    >>> await pdf_forms(operation="list_fields", path="form.pdf")
    {"success": true, "fields": [{"name": "name", "type": "text", "value": "", "page": 0, "rect": [...]}],
     "message": "Found 1 form fields in form.pdf."}

    >>> await pdf_forms(operation="fill", path="form.pdf", fields={"name": "Ada"})
    {"success": true, "path": ".../form_fill_....pdf",
     "message": "Filled 1 form fields in form.pdf, saved to form_fill_....pdf."}

    >>> await pdf_forms(operation="auto_fill", path="form.pdf", source="source.pdf")
    {"success": true, "path": ".../form_autofill_....pdf", "filled": 3, "missing": [],
     "message": "Auto-filled 3 fields in form.pdf from source.pdf."}
    """
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
                        if fields and name in fields:
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

        elif operation == "auto_fill":
            if not source and not text:
                return {"success": False, "error": "source (PDF path) or text is required for auto_fill."}
            try:
                from pdf_mcp.services.llm import chat_completion

                source_text = text or ""
                if source and not source_text:
                    src = fitz.open(source)
                    try:
                        source_text = " ".join(str(src[i].get_text()) for i in range(min(len(src), 20)))
                    finally:
                        src.close()
                doc = fitz.open(path)
                try:
                    fields_map: dict[str, dict] = {}
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        for widget in _get_widgets(page):
                            if widget.field_name:
                                fields_map[widget.field_name] = {
                                    "type": widget.field_type_string or "text",
                                    "label": widget.field_name,
                                }
                    if not fields_map:
                        return {"success": False, "error": "No fillable form fields found in the target PDF."}
                    import json as _json

                    prompt_fields = _json.dumps({k: v["label"] for k, v in fields_map.items()}, ensure_ascii=False)
                    reply = await chat_completion(
                        [
                            {
                                "role": "system",
                                "content": (
                                    "You extract form field values from a source document. "
                                    "Reply with a JSON object mapping each form field name to the most likely value "
                                    f"found in the source text. Form fields: {prompt_fields}. "
                                    "Only include fields you can support from the text. Reply with JSON only."
                                ),
                            },
                            {"role": "user", "content": source_text[:8000]},
                        ]
                    )
                    start = reply.find("{")
                    end = reply.rfind("}")
                    if start == -1 or end == -1:
                        return {"success": False, "error": "LLM returned no usable JSON mapping."}
                    values: dict = _json.loads(reply[start : end + 1])
                    op = output_path or _out_path(path, "autofill")
                    filled = 0
                    missing = []
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        for widget in _get_widgets(page):
                            name = widget.field_name
                            if name in values and values[name] not in (None, ""):
                                widget.field_value = str(values[name])
                                widget.update()
                                filled += 1
                    for name in fields_map:
                        if values.get(name) in (None, ""):
                            missing.append(name)
                    doc.save(op, garbage=4, deflate=True)
                    return {
                        "success": True,
                        "path": op,
                        "filled": filled,
                        "missing": missing,
                        "message": f"Auto-filled {filled} fields in {Path(path).name} from {'source' if source else 'text'}.",
                    }
                finally:
                    doc.close()
            except Exception as e:
                logger.exception("pdf_forms auto_fill failed: %s", e)
                return {"success": False, "error": str(e), "error_type": type(e).__name__}
    except Exception as e:
        logger.exception("pdf_forms %s failed: %s", operation, e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
