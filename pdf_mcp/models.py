from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ── Extract operations ──

PdfExtractOperation = Literal[
    "text",
    "images",
    "tables",
    "metadata",
    "fonts",
    "links",
    "outline",
]


# ── Manipulate operations ──

PdfManipulateOperation = Literal[
    "merge",
    "split",
    "rotate",
    "reorder",
    "delete_pages",
    "compress",
    "encrypt",
    "decrypt",
    "optimize",
]


# ── Annotate operations ──

PdfAnnotateOperation = Literal[
    "watermark",
    "stamp",
    "highlight",
    "underline",
    "header_footer",
    "page_numbers",
]


# ── Forms operations ──

PdfFormsOperation = Literal[
    "list_fields",
    "fill",
    "flatten",
    "export_data",
]


# ── Convert operations ──

PdfConvertOperation = Literal[
    "to_markdown",
    "to_images",
    "to_html",
    "from_html",
    "from_markdown",
    "from_images",
]


# ── Validate operations ──

PdfValidateOperation = Literal[
    "pdfa",
    "structure",
    "accessibility",
    "integrity",
    "compare",
]


# ── RAG operations ──

PdfRagOperation = Literal[
    "chunk",
    "index",
    "search",
    "list_documents",
    "delete_index",
]


# ── Job model ──


class PdfJob(BaseModel):
    job_id: str
    status: Literal["queued", "running", "complete", "failed"]
    operation: str
    params: dict = {}
    result_path: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None


# ── RAG chunk model ──


class PdfChunk(BaseModel):
    doc_id: str
    chunk_id: str
    page_num: int
    text: str
    section: str | None = None
    metadata: dict = {}
