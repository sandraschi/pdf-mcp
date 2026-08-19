# Troubleshooting

## Backend won't start on port 11131

```powershell
Get-NetTCPConnection -LocalPort 11131 -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

Then run `.\start.ps1` again. `start.ps1` clears zombie ports itself; this is the
manual fallback.

## `/api/health` reports `tool_count: 0`

The tool modules failed to register. Check the backend log for a circular-import or
import error. Tools register in `server.py main()` via `import pdf_mcp.tools`; any
exception there means zero tools. Run `uv run python -c "import pdf_mcp.server; import pdf_mcp.tools"` to surface it.

## Chat says "No local LLM detected"

Start Ollama (`ollama serve`) or LM Studio, then reload the Chat page. Detection
probes `127.0.0.1:11434` and `127.0.0.1:1234`. First chat request can be slow while
the model loads (10-60 s).

## Webapp pages Tools/Skills/Pipeline show errors

Those pages call `/api/tools`, `/api/skills`, `/api/jobs`. Confirm the backend is
running and the Vite proxy points at `127.0.0.1:11131` (see `webapp/vite.config.ts`).

## RAG operations fail with `The lance library is required`

`list_documents` no longer requires `pylance` (document counts are tracked
in-memory). If `index`/`search` fail, confirm the LanceDB store path is writable
(`RAG_STORE_PATH`) and that embeddings are produced.

## Tests fail with `Permission denied` on a temp PDF

Windows file lock: the test fixture must close the temp file before PyMuPDF saves
over it. Fixed in `tests/test_tools.py`; if you see it again, check for an open
`NamedTemporaryFile` handle.

## Pyright reports missing imports

Run pyright through the venv: `uv run --extra dev pyright pdf_mcp/`. A bare
`npx pyright` may not resolve the project venv.

## Still stuck?

- Check the live log tail: `http://127.0.0.1:11131/api/logs`
- File an issue at https://github.com/sandraschi/pdf-mcp/issues
