# Changelog

## 0.2.0 (2026-08-19)

- **Intelligence 2.0 feature set** (see `SPEC.md`): 22 features across RAG, extraction,
  automation, agentic tooling, and webapp.
  - New tools: `pdf_analyze` (scanned/digital), `pdf_redact` (terms + PII),
    `pdf_classify` (doc-type classifier), `pdf_dedupe` (fingerprint/near-dup),
    `pdf_export` (document brief), `pdf_do` (agentic chaining).
  - New operations: `pdf_rag` `similar` (query-by-example) + `synthesize`
    (cross-document, LLM summary), table-aware chunking, `source_file` in search hits;
    `pdf_forms` `auto_fill` (LLM-guided); `pdf_annotate` `summary_box`.
  - New REST: `/api/rag/search`, `/api/pdf/analyze`, `/api/pdf/compare`, `/api/pdf/dedupe`,
    `/api/recipes`, `/api/share/{job_id}`, `/api/share/{token}`, `/api/stats`,
    `/api/watch/status`.
  - Pipeline recipes (`ingest`, `redact_export`, `brief`) + watch-folder auto-process
    (`data/watch/`).
  - Webapp: Chat PDF search + source citations with jump-to-page, Workbench OCR badge +
    side-by-side compare mode + deep-link viewer, Pipeline recipes + share links,
    Dashboard usage stats panel.
  - 15 tests (was 8); all gates green (ruff, pyright, pytest, tsc, biome).

## 0.1.0 (2026-08-19)

- **assfix 2026-08-19**: repaired a runt server.
  - Fixed zero-tool registration bug: `server.py` now imports `pdf_mcp.tools`; `/api/health` reports 10 tools.
  - Fixed stdio transport (`run_stdio_async` now awaited) and the `/mcp` HTTP mount (FastMCP 3.4 `http_app` pattern).
  - Added missing webapp REST surface: `/api/tools`, `/api/skills`, `/api/skills/{name}`, `/api/chat`,
    `/api/llm/discover`, `/api/pdf/upload`, `/api/jobs`, `/api/logs`, `/api/pdf/files/{name}`.
  - Added `pdf_help`, `pdf_status`, `pdf_shutdown` tools.
  - Fixed service/tool signature mismatches (RAG constructor, chunker, extractor kwargs); pyright now clean (was 106 errors).
  - Fixed 2 failing tests (`test_manipulate_merge` temp-file lock, `test_rag_store_crud` `pylance` dependency).
  - Docstrings now carry `## Return Format` + `## Examples`; tools annotated (`ToolAnnotations`).
  - Added CI (five-gate: ruff/pyright/pytest/tsc/biome), pre-commit, `.gitattributes`, session-context
    injection (Claude Code, Cursor, Copilot, OpenCode, Antigravity), docs/ pages, `docs/INSTALL.md`,
    `.mcpbignore`, renovate.json.
  - Webapp: LLM elicitation (Ollama/LM Studio detect + provider/model select + Zustand store), skill-first
    chat system prompt, XSS-safe skills renderer, real PDF.js Workbench viewer + live job execution.

## 0.1.0 (2026-07-26)

- Initial release
- 7 portmanteau MCP tools: pdf_extract, pdf_manipulate, pdf_annotate, pdf_forms, pdf_convert, pdf_validate, pdf_rag
- 40+ PDF operations
- Webapp with 7 pages: Dashboard, Workbench, Pipeline, Chat, Tools, Skills, Logs
- Dual transport: stdio + HTTP
- LanceDB RAG index
- FastAPI REST API with CORS (Tauri + Tailscale + LAN)
