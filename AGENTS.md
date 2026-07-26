# pdf-mcp — Agent Navigation

## Reading order
1. `SPEC.md` — Full spec and architecture
2. `pdf_mcp/server.py` — Entry point, FastMCP app, REST API
3. `pdf_mcp/tools/` — 7 portmanteau tool files
4. `pdf_mcp/services/` — Core engines (Extractor, Manipulator, Converter, Chunker, RagStore)
5. `webapp/src/pages/` — React pages (Dashboard, Workbench, Pipeline, Chat, Tools, Skills, Logs)

## Key files

| File | Purpose |
|------|---------|
| `run_server.py` | Dual-transport entry point (stdio / HTTP) |
| `pdf_mcp/server.py` | FastMCP app, FastAPI REST, CORS, health endpoints |
| `pdf_mcp/config.py` | Env-based configuration |
| `pdf_mcp/tools/__init__.py` | Portmanteau tool registration |
| `pdf_mcp/services/extractor.py` | PyMuPDF text/image/table/metadata extraction |
| `pdf_mcp/services/manipulator.py` | pypdf merge/split/rotate/compress/encrypt |
| `pdf_mcp/services/converter.py` | PDF to/from Markdown/HTML/images |
| `pdf_mcp/services/chunker.py` | Text chunking strategies for RAG |
| `pdf_mcp/services/rag_store.py` | LanceDB vector store wrapper |
| `webapp/src/App.tsx` | React router + lazy-loaded pages |
| `webapp/src/pages/Dashboard.tsx` | KPI dashboard with health poll |
| `webapp/src/pages/Workbench.tsx` | PDF.js viewer + tool palette |
| `webapp/src/pages/Pipeline.tsx` | Batch job queue |
| `webapp/src/pages/Chat.tsx` | RAG-enabled LLM chat |

## Ports
- Backend: 11131 (HTTP + /mcp SSE)
- Frontend: 11130 (Vite dev server, proxies /api and /mcp)

## Commands
- `uv sync` — install Python deps
- `cd webapp && bun install` — install frontend deps
- `just serve` — start backend (HTTP mode on 11131)
- `cd webapp && bun run dev` — start frontend dev server
- `just test` — pytest
- `cd webapp && npx playwright test` — e2e tests
- `just lint` — ruff check
