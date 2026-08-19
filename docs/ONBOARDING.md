# Onboarding — pdf-mcp

## What this is for

Local **PDF intelligence**: extract, merge/split, annotate, forms, convert, validate,
redact, classify, dedupe, and LanceDB RAG — via MCP tools (16 total, incl. the
agentic `pdf_do`) and a PDF.js workbench with compare mode and chat-driven source
search.

## Cost

| Question | Answer |
|----------|--------|
| Cloud OCR? | No — PyMuPDF / pypdf / pdfplumber on your machine |
| GPU? | Optional for embedding models if you enable RAG extras |
| Disk? | Uploads + LanceDB under `data/` |
| LLM? | Optional (Ollama / LM Studio) — enables `pdf_do`, auto-fill, summaries |

## Setup

```powershell
cd D:\Dev\repos\pdf-mcp
uv sync
Copy-Item .env.example .env
cd webapp
bun install
cd ..
.\start.ps1
```

Fleet launcher: `mcp-central-docs\starts\pdf-mcp-start.bat`

- Dashboard: http://127.0.0.1:11130
- Backend / MCP: http://127.0.0.1:11131

## Pitfalls

- Large scanned PDFs: run `pdf_analyze` first — if it reports `scanned`, use OCR
  elsewhere before extracting text (this stack is text-layer oriented)
- RAG optional deps: `uv sync --extra rag` when using semantic search
- Keep secrets out of uploaded PDFs you index into LanceDB — or run `pdf_redact`
  with `pii: true` before indexing
- LLM features need a local LLM: start Ollama (`ollama serve`) or LM Studio
- Watch-folder: drop PDFs into `data/watch/` to auto-run the `ingest` recipe
