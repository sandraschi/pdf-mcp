# pdf-mcp — Agent Navigation

## Reading order
1. `SPEC.md` — Full spec, architecture, and the Intelligence 2.0 feature set
2. `pdf_mcp/server.py` — Entry point, FastMCP app, Starlette HTTP + REST API
3. `pdf_mcp/tools/` — Portmanteau tool modules (extract, manipulate, annotate, forms, convert, validate, rag, intel, agent, meta)
4. `pdf_mcp/services/` — Core engines (Extractor, Manipulator, Converter, Chunker, RagStore, Intel, Llm)
5. `webapp/src/pages/` — React pages (Dashboard, Workbench, Pipeline, Chat, Tools, Skills, Logs)

## Key files

| File | Purpose |
|------|---------|
| `run_server.py` | Dual-transport entry point (stdio / HTTP) |
| `pdf_mcp/server.py` | FastMCP app, Starlette HTTP app, REST endpoints, recipes, watch-folder, share links, stats |
| `pdf_mcp/config.py` | Env-based configuration |
| `pdf_mcp/tools/__init__.py` | Tool module registration |
| `pdf_mcp/tools/agent.py` | `pdf_do` agentic chaining tool |
| `pdf_mcp/tools/intel.py` | `pdf_analyze`, `pdf_redact`, `pdf_classify`, `pdf_dedupe`, `pdf_export` |
| `pdf_mcp/tools/meta.py` | `pdf_help`, `pdf_status`, `pdf_shutdown` |
| `pdf_mcp/services/intel.py` | Analyzer, Redactor, Classifier, Deduper, BriefBuilder |
| `pdf_mcp/services/llm.py` | Local LLM discovery + chat completions (Ollama / LM Studio) |
| `pdf_mcp/services/extractor.py` | PyMuPDF text/image/table/metadata extraction |
| `pdf_mcp/services/manipulator.py` | pypdf merge/split/rotate/compress/encrypt |
| `pdf_mcp/services/converter.py` | PDF to/from Markdown/HTML/images |
| `pdf_mcp/services/chunker.py` | Text chunking strategies (incl. table-aware) |
| `pdf_mcp/services/rag_store.py` | LanceDB vector store wrapper |
| `webapp/src/App.tsx` | React router + lazy-loaded pages |
| `webapp/src/pages/Dashboard.tsx` | KPI dashboard + usage stats panel |
| `webapp/src/pages/Workbench.tsx` | PDF.js viewer + tool palette + compare mode |
| `webapp/src/pages/Pipeline.tsx` | Batch jobs + recipes + share links |
| `webapp/src/pages/Chat.tsx` | LLM chat + PDF search / sources panel |
| `webapp/src/lib/api.ts` | Fetch layer (REST + RAG search + share + stats) |
| `webapp/src/lib/store.ts` | Zustand store (backend + LLM provider/model state) |

## Ports
- Backend: 11131 (HTTP, `/mcp` streamable HTTP, `/api/*` REST)
- Frontend: 11130 (Vite dev server, proxies /api and /mcp)

## Commands
- `uv sync --extra dev --extra test` — install Python deps + dev/test extras
- `cd webapp && bun install` — install frontend deps
- `just serve` — start backend (HTTP mode on 11131)
- `just dev` — backend + frontend
- `just lint` / `just pyright` / `just test` / `just tsc` / `just ci` — gates
- `just e2e` — Playwright e2e
- `just bootstrap` — dev deps + pre-commit hooks + webapp deps
