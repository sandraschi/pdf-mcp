# Onboarding — pdf-mcp

## What this is for

Local **PDF intelligence**: extract, merge/split, annotate, forms, convert, validate, and LanceDB RAG — via MCP tools and a PDF.js workbench.

## Cost

| Question | Answer |
|----------|--------|
| Cloud OCR? | No — PyMuPDF / pypdf / pdfplumber on your machine |
| GPU? | Optional for embedding models if you enable RAG extras |
| Disk? | Uploads + LanceDB under `data/` |

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

- Large scanned PDFs need OCR elsewhere first (this stack is text-layer oriented)
- RAG optional deps: `uv sync --extra rag` when using semantic search
- Keep secrets out of uploaded PDFs you index into LanceDB
