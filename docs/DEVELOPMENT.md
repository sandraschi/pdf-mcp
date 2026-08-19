# Development

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh) for the webapp
- Optional: [just](https://github.com/casey/just) for the task recipes

## Setup

```powershell
uv sync --extra dev --extra test
cd webapp && bun install
```

## Running

| Task | Command |
|------|---------|
| Backend (HTTP) | `uv run python run_server.py --mode http --port 11131` |
| Frontend dev server | `bun run --cwd webapp dev` |
| Both via start script | `.\start.ps1` |
| MCP stdio (Claude Desktop) | `uv run python run_server.py` |

Ports: backend `11131`, frontend `11130`.

## Structure

```
pdf_mcp/
  server.py         FastMCP app + Starlette HTTP app + REST endpoints
                    (recipes, watch-folder, share links, usage stats)
  config.py         Env-based configuration
  models.py         Pydantic models + operation Literals
  tools/            Portmanteau tool modules
    extract.py      pdf_extract
    manipulate.py   pdf_manipulate
    annotate.py     pdf_annotate (incl. summary_box)
    forms.py        pdf_forms (incl. auto_fill)
    convert.py      pdf_convert
    validate.py     pdf_validate
    rag.py          pdf_rag (search / similar / synthesize)
    intel.py        pdf_analyze, pdf_redact, pdf_classify, pdf_dedupe, pdf_export
    agent.py        pdf_do (agentic chaining)
    meta.py         pdf_help, pdf_status, pdf_shutdown
  services/         Core engines
    extractor.py    PyMuPDF text/image/table/metadata extraction
    manipulator.py  pypdf merge/split/rotate/compress/encrypt
    converter.py    PDF to/from Markdown/HTML/images
    chunker.py      Text chunking (recursive, fixed, table-aware)
    rag_store.py    LanceDB vector store wrapper
    intel.py        Analyzer, Redactor, Classifier, Deduper, BriefBuilder
    llm.py          Local LLM discovery + chat completions
  skills/           Agent skill definitions
webapp/
  src/pages/        Dashboard, Workbench, Pipeline, Chat, Tools, Skills, Logs
  src/lib/          api.ts (fetch layer) + store.ts (Zustand incl. LLM state)
```

## Recipes

`POST /api/jobs` with `{recipe, params}` runs a multi-step recipe (`pdf_mcp/server.py`
`RECIPES`):

| Recipe | Steps |
|--------|-------|
| `ingest` | analyze → index → export_brief |
| `redact_export` | analyze → redact(pii) → export_brief |
| `brief` | export_brief |

Watch-folder: drop PDFs into `data/watch/` while the HTTP server runs; the `ingest`
recipe runs automatically and results appear in job history.

## Recipes

| Recipe | Purpose |
|--------|---------|
| `just serve` | Start backend (HTTP) |
| `just dev` | Start backend + frontend |
| `just lint` | ruff check + format --check |
| `just pyright` | Python type gate |
| `just test` | pytest |
| `just tsc` | Webapp typecheck |
| `just e2e` | Playwright e2e |
| `just ci` | All five gates |
| `just bootstrap` | dev deps + pre-commit hooks + webapp deps |

## Gates (five-gate shape)

1. ruff (style) — `just lint`
2. pyright (Python types) — `just pyright`
3. tsc (TypeScript types) — `just tsc`
4. pytest (behavior) — `just test`
5. Biome (frontend style) — `bun run --cwd webapp biome:ci`

All five run in CI (`.github/workflows/ci.yml`). Keep them green before pushing.
