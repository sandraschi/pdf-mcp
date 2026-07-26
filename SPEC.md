# SPEC: pdf-mcp

**Status**: Draft
**Date**: 2026-07-26

## Goal

A full-stack PDF intelligence MCP server with a webapp workbench — merge, split, extract, annotate, convert, validate, and RAG-search PDFs. Designed to eclipse the hundreds of 3-tool PDF MCP wrappers on GitHub with genuine depth.

## Requirements

### Backend

- [ ] **7 portmanteau tools** covering the full PDF lifecycle
- [ ] Dual transport: stdio (Claude Desktop / Cursor) + HTTP (webapp / Tauri)
- [ ] Pure Python — no LibreOffice, no external binaries (WebView2 only for Tauri)
- [ ] REST API endpoints for webapp: `/api/pdf/*`, `/api/health`, `/api/v1/diagnostics`
- [ ] CORS middleware (Tauri origins + Tailscale + LAN)

### Tool Portmanteaus

1. **`pdf_extract`** — extract text, images, tables, metadata, fonts, links, table of contents
2. **`pdf_manipulate`** — merge, split, rotate, reorder, delete pages, compress, encrypt, decrypt, optimize
3. **`pdf_annotate`** — watermark (text/image), text/stamp annotation, highlight/underline, header/footer, page numbers
4. **`pdf_forms`** — list form fields, fill form, flatten form, export form data (JSON/FDF)
5. **`pdf_convert`** — PDF → Markdown, PDF → Images (per-page PNG/JPEG), HTML/Markdown → PDF
6. **`pdf_validate`** — PDF/A compliance, structure check, accessibility (tags/headings), file integrity, document comparison
7. **`pdf_rag`** — chunk document (section-aware, by page, recursive), index chunks to LanceDB, semantic search, list indexed documents, delete index

### Webapp (7 pages)

- [ ] **Dashboard** — backend health, tool count, recent PDFs, storage stats. data-testid on KPIs, exponential backoff health check
- [ ] **Workbench** — PDF.js viewer + tool palette sidebar. Load PDF, flip pages, run extract/annotate/convert operations interactively
- [ ] **Pipeline** — upload PDF → select operation → configure params → execute → download results. Job queue with status tracking
- [ ] **Chat** — LLM chat with RAG context from indexed PDFs. Personality selector, example prompts, export, clear
- [ ] **Tools** — dynamic tool discovery from server, portmanteau drill-down, docstring rendering
- [ ] **Skills** — load and display skill content
- [ ] **Logs** — JSON-RPC log viewer

### Technical Stack

- **Backend**: Python, FastMCP 3.4+, FastAPI, PyMuPDF, pypdf, pdfplumber, LanceDB
- **Frontend**: React + Vite + Tailwind + Lucide + Zustand + Framer Motion + PDF.js
- **Package manager**: Bun (committed `bun.lock`)
- **Packaging**: pyproject.toml + uv.lock + justfile + glama.json + llms.txt/llms-full.txt
- **Ports**: 11130 (frontend) / 11131 (backend) — adjacent pair, clean in fleet registry
- **Docs**: README.md, CHANGELOG.md, INSTALL.md, SKILL.md

## Non-goals

- OCR (that's ocr-mcp's job — we link to it for scanned PDFs)
- Digital signatures / certificate management (future)
- Tauri/NSIS wrapper in v1 (add after core is solid)
- Multi-user or auth (local-first, single-user)
- PDF generation from scratch (we convert from HTML/Markdown, not compose programmatic PDFs)

## API / Interface

### MCP Tools (7 portmanteaus, ~40 operations)

Each portmanteau follows the industrial portmanteau pattern with `operation: Literal[...]` as first param, `Annotated` fields with `description`, and docstrings with `## Return Format` + `## Examples`.

### REST Endpoints

```
GET  /api/health              → { status, version, uptime, tool_count }
GET  /api/v1/diagnostics      → { status, tools, system }
POST /api/pdf/upload          → multipart file → { job_id, pages, size }
GET  /api/pdf/{job_id}/status → { status, progress, download_url }
GET  /api/pdf/{job_id}/result → file download
GET  /api/skills              → skill list
GET  /api/skills/{name}       → raw SKILL.md content
```

### Webapp Routes

```
/           → Dashboard
/workbench  → PDF Workbench (viewer + tools)
/pipeline   → Batch operations
/chat       → LLM Chat (RAG)
/tools      → Tool explorer
/skills     → Skills
/logs       → JSON-RPC log viewer
```

## Dependencies

### Python (core)

| Package | Purpose |
|---------|---------|
| `fastmcp>=3.4` | MCP framework |
| `fastapi` | REST API |
| `uvicorn[standard]` | HTTP server |
| `pymupdf` | PDF rendering, text/image/link extraction, page ops |
| `pypdf` | Merge, split, encrypt, forms, metadata |
| `pdfplumber` | Table extraction |
| `lancedb` | Local vector store for RAG |
| `prefab-ui>=0.14` | Rich in-chat Prefab cards |
| `Pillow` | Image processing for PDF→images |

### Frontend (dev + prod)

| Package | Purpose |
|---------|---------|
| `react`, `react-dom`, `react-router-dom` | SPA framework |
| `vite` | Bundler |
| `tailwindcss` | Styling |
| `lucide-react` | Icons |
| `zustand` | State management |
| `framer-motion` | Animations |
| `pdfjs-dist` | In-browser PDF rendering |
| `@playwright/test` | E2E tests |

## Data model

### Jobs (in-memory + optional SQLite persistence)

```python
class PdfJob(BaseModel):
    job_id: str
    status: Literal["queued", "running", "complete", "failed"]
    operation: str
    params: dict
    result_path: str | None
    error: str | None
    created_at: datetime
```

### RAG Index (LanceDB)

```python
class PdfChunk(BaseModel):
    doc_id: str
    chunk_id: str
    page_num: int
    text: str
    section: str | None
    metadata: dict  # source file, title, author, date
    vector: list[float]  # embedding
```

## Files changed / created

```
pdf-mcp/
├── SPEC.md                         ← this file
├── pyproject.toml                  ← project config + deps
├── uv.lock                         ← lockfile
├── justfile                        ← recipes: serve, test, lint, fmt
├── glama.json                      ← Glama discovery
├── llms.txt                        ← LLM index
├── llms-full.txt                   ← full LLM corpus
├── run_server.py                   ← dual-transport entry point
├── .env.example                    ← env vars
├── .gitignore
├── start.ps1                       ← dev startup
├── start.bat                       ← double-click wrapper
├── pdf_mcp/
│   ├── __init__.py
│   ├── server.py                   ← FastMCP app + lifespan
│   ├── config.py                   ← env-based config
│   ├── models.py                   ← Pydantic models
│   ├── tools/
│   │   ├── __init__.py             ← portmanteau imports
│   │   ├── extract.py
│   │   ├── manipulate.py
│   │   ├── annotate.py
│   │   ├── forms.py
│   │   ├── convert.py
│   │   ├── validate.py
│   │   └── rag.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── extractor.py
│   │   ├── manipulator.py
│   │   ├── converter.py
│   │   ├── chunker.py
│   │   └── rag_store.py
│   ├── skills/
│   │   └── pdf-expert/
│   │       └── SKILL.md
│   └── resources/
├── webapp/
│   ├── package.json
│   ├── bun.lock
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── playwright.config.ts
│   ├── e2e/
│   │   └── audit.spec.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── lib/
│       │   ├── api.ts
│       │   └── store.ts
│       ├── components/
│       │   ├── AppLayout.tsx
│       │   ├── Topbar.tsx
│       │   ├── Sidebar.tsx
│       │   ├── BackendDot.tsx
│       │   └── PdfViewer.tsx
│       └── pages/
│           ├── Dashboard.tsx
│           ├── Workbench.tsx
│           ├── Pipeline.tsx
│           ├── Chat.tsx
│           ├── Tools.tsx
│           ├── Skills.tsx
│           └── Logs.tsx
└── tests/
    └── test_tools.py
```

## Test plan

1. `ruff check` + `ruff format` — zero errors
2. `pytest` — unit test each portmanteau operation with sample PDFs
3. `playwright test` — webapp: dashboard loads, workbench loads PDF, pipeline runs job
4. Manual: verify Claude Desktop can call tools via stdio
5. Manual: verify webapp can call backend via HTTP

## Open questions

- Should RAG chunking default to sentence-window or section-aware (outline-based)?
- LanceDB for embeddings — use built-in embedding function or require OpenAI-compatible API?
- PDF compression strategy: downscale images (PyMuPDF) vs pypdf compress? Both configurable?
- Should we support password-protected PDFs on decrypt operations? (yes, with `password` param)

## Approval

**Status**: Draft — awaiting user approval before implementation
