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
  config.py         Env-based configuration
  models.py         Pydantic models + operation Literals
  tools/            Portmanteau tool modules (extract, manipulate, annotate,
                    forms, convert, validate, rag, meta)
  services/         Core engines (extractor, manipulator, converter, chunker, rag_store)
  skills/           Agent skill definitions
webapp/
  src/pages/        Dashboard, Workbench, Pipeline, Chat, Tools, Skills, Logs
  src/lib/          api.ts (fetch layer) + store.ts (Zustand)
```

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
