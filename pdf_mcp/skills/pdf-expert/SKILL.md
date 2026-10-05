# pdf-mcp — Skill

## Overview

pdf-mcp is a full-stack, local-first PDF intelligence MCP server. It exposes **16
portmanteau tools** (`operation`-selected) covering extraction, manipulation, annotation,
forms, conversion, validation, redaction, classification, deduplication, RAG, briefs, and
an agentic chaining tool. The only optional dependency is a local LLM (Ollama / LM Studio)
for chat, `pdf_do`, auto-fill, and summaries. Everything else works offline.

## Audience routing

- **Agent, exploratory task** ("what's in this PDF?", "find the clause") → start read-only:
  `pdf_analyze` → `pdf_extract(metadata|outline|text)` → `pdf_rag(search)`.
- **Agent, chained multi-step task** → `pdf_do(task=..., path=...)` (needs a local LLM).
- **Agent, structured pipeline** → drive the operations explicitly and inspect each
  `success` before continuing.
- **Human at the webapp** → Workbench (view/compare/one-off tools), Pipeline (batch +
  recipes), Chat (asks), Settings (LLM setup), Inbox (watch folder), Logs.
- **Human scripting** → the REST surface (`/api/jobs`, `/api/rag/search`, `/api/health`).

## Tool catalogue (all 16)

Read-only inspection:

- **`pdf_analyze`** — `scanned` vs digital, per-page layout stats. Always run before
  extraction on an unknown file.
- **`pdf_extract`** — ops: `text`, `images`, `tables`, `metadata`, `fonts`, `links`,
  `outline`. Optional 1-indexed `pages` range.
- **`pdf_validate`** — ops: `pdfa`, `structure`, `accessibility`, `integrity`, `compare`.
- **`pdf_classify`** — document type (invoice, receipt, report, contract, form, resume,
  letter, …). `refine=true` uses the LLM.
- **`pdf_dedupe`** — exact + near duplicates over `paths`, `threshold` (default 0.85).
- **`pdf_rag`** — ops: `chunk`, `index`, `search`, `similar`, `synthesize`,
  `list_documents`, `delete_index`. Hits carry `source_file` + `page_num`.

Write (returns a new path; original untouched):

- **`pdf_manipulate`** — ops: `merge`, `split`, `rotate`, `reorder`, `delete_pages`,
  `compress`, `encrypt`, `decrypt`, `optimize`.
- **`pdf_annotate`** — ops: `watermark`, `stamp`, `highlight`, `underline`,
  `header_footer`, `page_numbers`, `summary_box` (LLM).
- **`pdf_convert`** — ops: `to_markdown`, `to_images`, `to_html`, `from_html`,
  `from_markdown`, `from_images`.
- **`pdf_forms`** — ops: `list_fields`, `fill`, `flatten`, `export_data`, `auto_fill` (LLM).
- **`pdf_redact`** — blacken `terms` and/or `pii=true` (email, phone, IBAN, card, SSN, IP).
- **`pdf_export`** — document brief as `markdown`/`json`, optional LLM summary.

Agentic + meta:

- **`pdf_do`** — plan + chain tools from a natural-language `task` (LLM required).
- **`pdf_help`** — list tools or one tool's schema.
- **`pdf_status`** — version, uptime, tool count, mode.
- **`pdf_shutdown`** — graceful stop (destructive; only on explicit request).

## Workflows (copy-shape)

**Inspect → act** (never manipulate what you haven't inspected):

```
pdf_analyze(path=...)                       # scanned?
pdf_extract(operation="metadata", path=...)
pdf_extract(operation="outline", path=...)
```

**Searchable corpus**:

```
pdf_rag(operation="index", path=...)        # note doc_id
pdf_rag(operation="search", query=..., limit=8)
pdf_rag(operation="synthesize", query=...)  # grounded answer (LLM optional)
pdf_rag(operation="delete_index", doc_id=...)  # when superseded
```

**Clean before sharing**:

```
pdf_redact(path=..., pii=true)              # -> new path
pdf_extract(operation="text", path=<redacted>)  # verify
```

**Pipeline batch** (HTTP): `POST /api/jobs {"recipe":"ingest"|"redact_export"|"brief",
"params":{"filename":...}}`, or drop PDFs in `data/watch/` for automatic `ingest`.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `MCP_MODE` | `stdio` | `stdio` or `http` |
| `MCP_PORT` / `FRONTEND_PORT` | 11131 / 11130 | HTTP ports |
| `RAG_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | embedding model |
| `RAG_STORE_PATH` | `data/lancedb` | vector store |
| `UPLOAD_DIR` | `data/uploads` | outputs |

## Troubleshooting

- **Empty extraction** → the PDF is scanned (`pdf_analyze` confirms). OCR elsewhere first.
- **No RAG results** → nothing indexed (`pdf_rag(list_documents)`) or the `rag` extra is
  missing (`uv sync --extra rag`) so only the weak hash-embedding fallback runs.
- **Chat/`pdf_do` say "no LLM"** → start Ollama (`ollama serve`) or LM Studio, then
  `pdf_help`/Settings to confirm detection.
- **`fill` changes nothing** → run `list_fields` and match names exactly.
- **Can't find an output** → every write tool returns the full path under `UPLOAD_DIR`.
- **Backend dot red** → backend not started or wrong port; check `GET /api/health`.

## Safety

Local-first, no uploads. Mutations write new files. Redaction is irreversible on the output
— work on a copy and verify by extraction. Do not index documents containing secrets you
would not keep locally. `pdf_shutdown` only on explicit request.
