# pdf-mcp — Feature Spec: Intelligence 2.0

**Status:** approved 2026-08-19 · **Scope:** 22 features across RAG, extraction, automation,
agentic tooling, and the webapp. All build on the existing stack (FastMCP 3.4.4, PyMuPDF,
pypdf, pdfplumber, LanceDB, local LLM via Ollama/LM Studio).

## Implementation tiers

| Tier | Scope | Gate |
|------|-------|------|
| 1 | Backend tools + REST + RAG + automation (everything below that is testable headless) | ruff, pyright, pytest green |
| 2 | Agentic `pdf_do` + auto annotations | same + manual smoke |
| 3 | Webapp (Chat sources, OCR badges, share links, stats, compare, thumbnails) | tsc, biome green |

---

## 1. Ask-your-PDF with page citation + highlight jump

**Goal:** chat answers cite source pages; clicking a citation opens the Workbench viewer at
that page.

- `pdf_rag.search` results already carry `page_num`. Extend each chunk to also carry
  `source_file` (the indexed filename) and store it in LanceDB metadata.
- New REST `POST /api/rag/search` `{query, limit}` → synchronous results for the Chat page.
- Chat renders a **Sources** panel per assistant message: doc, page, snippet; each row is a
  button `Open page N` → `navigate('/workbench?file=<name>&page=N')`.
- Workbench reads `?file=&page=` on mount: if the file is in the upload registry, load it,
  jump to the page, and flash-highlight the region for 2 s.
- If the file is not currently uploaded, Workbench shows a clear "re-upload to view" hint.

**Files:** `pdf_mcp/services/rag_store.py`, `pdf_mcp/tools/rag.py`, `pdf_mcp/server.py`,
`webapp/src/pages/Chat.tsx`, `webapp/src/pages/Workbench.tsx`, `webapp/src/lib/api.ts`.

## 2. Cross-document synthesis

**Goal:** answer questions across the whole index with per-doc evidence.

- New `pdf_rag` op `synthesize`: runs the search, groups hits by `doc_id`, and returns
  `{groups: [{doc_id, source_file, hits: [...], snippet}]}`.
- When a local LLM is available, an optional `summary` field is produced by the LLM from the
  top hits. Never blocks on the LLM — fall back to grouped passages with a `llm: false` flag.

## 3. Table-aware RAG

**Goal:** tables become queryable structured chunks instead of flattened text.

- `chunker` gains `chunk_with_tables(text, tables, metadata, ...)`: each extracted table is
  emitted as its own chunk with `section: "table"` and a markdown-style `|` rendering; body
  text is chunked as before.
- `pdf_rag index` extracts tables (pdfplumber) when present and passes them in.
- `pdf_rag search` results include `section` so "compare the Q3 rows" queries hit the table
  chunks.

## 4. Query-by-example / RAG round-trip

**Goal:** "find passages like this one."

- New `pdf_rag` op `similar`: takes a `text` snippet, embeds it, runs vector search, returns
  the N nearest passages with doc/page/source.
- Chat: user selects text in a message and the app issues a `similar` search to fill the
  Sources panel.

## 5. Document fingerprints / dedupe

**Goal:** detect near-duplicate uploads before they pollute the index.

- New tool `pdf_dedupe(paths: list[str], threshold: float = 0.85)`: for each PDF, extract text
  and build a content fingerprint (normalized text SHA-256 + length). Pairwise
  `difflib.SequenceMatcher` on normalized text gives similarity; pairs above threshold are
  reported.
- REST `POST /api/pdf/dedupe` powers a webapp check button.

## 6. Auto-fill forms (LLM-guided)

**Goal:** fill a form from a source document.

- New `pdf_forms` op `auto_fill`:
  - `path` = the fillable form; `source` = a source PDF or `text` = raw text.
  - Extract field names/labels via the existing widget walk.
  - Local LLM maps `field_name → value` given the source text (prompt returns JSON only).
  - Fills and saves; returns `{path, filled, missing}`.
  - No LLM available → returns `{success:false, error:"LLM required"}` (declared, not a mock).

## 7. Document auto-classifier

**Goal:** guess the document type and normalize a schema.

- New tool `pdf_classify(path)` → `{doc_type, confidence, fields, reasons}`.
  - Doc types: invoice, receipt, report, contract, form, resume, presentation, letter, scanned-document, other.
  - Heuristic pass: metadata + first-page keyword/ratio signals, returns `fields` candidates
    (totals, vendor, dates) with regex.
  - Optional LLM refinement when available (takes the heuristic output as context).

## 8. Redaction by intent

**Goal:** blacken sensitive content.

- New tool `pdf_redact(path, terms?: list[str], pii?: bool, output_path?)`:
  - `terms`: exact phrases to blacken (search_for → redact annot → apply).
  - `pii`: regex PII set — email, phone, IBAN, credit card, SSN/ID, IP address.
  - `fill` color option (default black). Returns `{path, occurrences}`.
- REST `POST /api/pdf/redact` for webapp use.

## 9. OCR readiness detection

**Goal:** know whether a PDF has a text layer.

- New tool `pdf_analyze(path)` → `{has_text_layer, scanned (bool), pages, chars_per_page,
  image_count, layout_hint}`.
  - `has_text_layer` = avg chars/page above threshold.
  - `scanned` = low text + high image density.
- Webapp shows an **OCR** badge on uploads; a future `tesseract`-backed OCR op is out of
  scope for this pass (documented in TROUBLESHOOTING).

## 10. Watch-folder auto-process

**Goal:** drop a PDF in `data/watch/` and let the server ingest it.

- Background task started with the HTTP server: polls `data/watch/*.pdf` every 5 s.
- New file → run the `ingest` recipe (see #13): analyze → index → summarize, record in job
  history with `source: watch`.
- REST `GET /api/watch/status` → `{watching, processed, errors}`.

## 11. Batch comparison dashboard

**Goal:** side-by-side diff in the webapp.

- Backend: `pdf_validate compare` already returns text diffs; add REST
  `POST /api/pdf/compare` `{path_a, path_b}` for synchronous access.
- Workbench **Compare mode**: two file slots, two PDF.js canvases rendered page-by-page with
  synchronized page control, plus a diff panel showing the top textual differences.

## 12. Template extraction

**Goal:** build a layout map once, extract the same fields from a batch.

- New tool `pdf_template` with ops:
  - `create(path)` → extracts widget/field positions + text anchors → returns a template map (JSON).
  - `apply(path, template)` → re-runs extraction at the recorded anchor regions.
- Scoped as a stretch goal: if the widget walk already returns rects, `create` is a thin
  wrapper; `apply` re-uses `pdf_forms list_fields` logic.

## 13. Pipeline recipes

**Goal:** named, reusable multi-step jobs.

- Backend recipe registry (in `server.py`): `ingest`, `redact_export`, `brief`.
  - `ingest` = analyze → index → summarize.
  - `redact_export` = analyze → redact(pii) → export brief.
  - `brief` = export brief only.
- `POST /api/jobs` accepts `{recipe, params}`; expands to ordered steps; job records
  `step`/`steps` in its status payload. `GET /api/recipes` lists recipes.

## 14. `pdf_do` — PDF agent tool

**Goal:** one tool that chains the others from natural language.

- New tool `pdf_do(task: str, path?: str)`:
  - Requires a local LLM (declared failure otherwise).
  - LLM produces a JSON plan: up to 6 steps, each `{tool, args}` chosen from the pdf_* surface.
  - The server executes each step (calling the actual tool functions), feeding prior results
    back; final LLM pass writes a natural-language answer.
  - Strict guardrails: allowed tool list, max 6 steps, args validated against tool schemas,
    `pdf_shutdown` and `pdf_do` are not callable from the plan.

## 15. Self-writing annotations (auto summary box)

**Goal:** LLM writes content into the PDF.

- New `pdf_annotate` op `summary_box`: LLM summarizes the document; the text is stamped as an
  annotation box at the top of page 1 (reuses stamp machinery). `{path, summary}`.

## 16. Chat result links

**Goal:** chat answers link to downloadable artifacts.

- `/api/chat` response may include `artifacts: [{label, job_id, url}]` when the conversation
  produced a file (e.g. after an export). Chat renders an inline download chip.

## 17. Shareable result links

**Goal:** short-lived shareable downloads.

- REST `POST /api/share/{job_id}` → `{url: /api/share/{token}}` with 24 h expiry; the token
  is opaque and cached in an in-memory registry.
- `GET /api/share/{token}` streams the job result file (404/410 on expiry).
- Workbench/Pipeline get a "Copy share link" button.

## 18. Usage analytics

**Goal:** Dashboard shows what the server does.

- In-memory stats registry: per-operation `{count, total_ms, avg_ms, last_at}` updated in
  `_execute_job`.
- REST `GET /api/stats` → `{operations: [...], total_jobs, total_files}`.
- Dashboard renders a small table (top ops by count) under the KPIs.

## 19. OCR status badges (webapp)

- On upload, Workbench calls `pdf_analyze` (REST) and shows a `Scanned` / `Digital` badge +
  page/text stats in the viewer header.

## 20. Thumbnail rail (webapp)

- Workbench renders a vertical strip of per-page thumbnails (PDF.js, small scale) on the
  left of the viewer; click a thumbnail to jump. Only the current window of pages renders
  to keep it fast.

## 21. `pdf_export` — document brief

**Goal:** one tool producing a reusable brief.

- New tool `pdf_export(path, format: "markdown"|"json", include_summary: bool)`:
  - Extracts text, metadata, outline; builds a structured brief (headings detected, first N
    paragraphs, key terms via simple frequency).
  - Optional LLM summary appended when available.
  - Writes `<stem>_brief.md|.json` to `data/uploads` and returns `{path, pages, summary?}`.

## 22. Cross-cutting rules

- Every new MCP tool: `## Return Format` + `## Examples` docstrings, `ToolAnnotations`,
  `logger.exception` in except blocks, `{success, message, data}`-style returns.
- New REST endpoints follow the existing Starlette `add_route` pattern with JSON responses.
- Local LLM use is always optional and fail-soft (never blocks a non-LLM feature).
- No `print()`, no `console.log`, no bare `except:`, no `# type: ignore` without a code.
- Gates stay green: ruff, pyright, pytest, tsc, biome.
