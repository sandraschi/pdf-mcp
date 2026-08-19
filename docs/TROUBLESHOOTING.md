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

## New in 0.2 (Intelligence 2.0)

### LLM-dependent features say "no local LLM"
`pdf_do`, `pdf_forms auto_fill`, `pdf_annotate summary_box`, `pdf_rag synthesize`
summaries, and `pdf_export` summaries require a local LLM. Start Ollama
(`ollama serve`) or LM Studio. All non-LLM features (extract, manipulate, validate,
analyze, redact, classify, dedupe, search) work without one.

### `pdf_rag index` fails with "field does not exist in table schema"
A stale LanceDB table from before the `source_file` column was added. The server
auto-migrates on the next index attempt (drops and rebuilds the table). To force a
clean reset: stop the server, delete `data/lancedb/`, restart, and re-index.

### Watch-folder does nothing
`data/watch/` is created on HTTP startup. Make sure the server runs in HTTP mode
(`uv run python run_server.py --mode http`) and drop a `.pdf` there. Check
`/api/watch/status` for processed/errors.

### Share link returns 410
Share tokens expire after 24 h (in-memory registry). Re-create the link via
`POST /api/share/{job_id}`. Restarting the server invalidates all tokens.

### RAG search returns no results
You must index first (`pdf_rag index` or the `ingest` recipe). `search`, `similar`,
and `synthesize` only search what has been indexed. Check `pdf_rag list_documents`.
