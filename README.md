# pdf-mcp

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.4.4-7c5cfc?style=flat-square" alt="FastMCP"></a>
  <a href="https://www.adobe.com/acrobat/about-adobe-pdf.html"><img src="https://img.shields.io/badge/PDF-intelligence-E5252A?style=flat-square" alt="PDF"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="MIT"></a>
</p>

Full-stack **PDF intelligence** MCP server — extract, manipulate, annotate, convert, validate, and RAG-search PDFs through a unified tool surface and React workbench.

**v0.1.0** · Ports **11130** (frontend) / **11131** (backend)

> FastMCP 3.4.4 · PyMuPDF + pypdf + pdfplumber · LanceDB RAG · Prefab UI · dual transport (stdio + HTTP)

## Features

- **pdf_extract** — text, images, tables, metadata, fonts, links, outline
- **pdf_manipulate** — merge, split, rotate, reorder, delete pages, compress, encrypt/decrypt, optimize
- **pdf_annotate** — watermark, stamp, highlight, underline, header/footer, page numbers
- **pdf_forms** — list / fill / flatten / export form fields
- **pdf_convert** — PDF ↔ Markdown / images / HTML
- **pdf_validate** — PDF/A, structure, accessibility, integrity, compare
- **pdf_rag** — chunk, index (LanceDB), semantic search
- **pdf_help / pdf_status / pdf_shutdown** — meta tools

## Quick start

```powershell
git clone https://github.com/sandraschi/pdf-mcp
cd pdf-mcp
uv sync
Copy-Item .env.example .env
.\start.ps1
```

Dashboard: http://127.0.0.1:11130 · MCP/API: http://127.0.0.1:11131

## Stack

- **Backend**: Python 3.12, FastMCP 3.4.4, Starlette (HTTP), PyMuPDF, pypdf, pdfplumber, LanceDB, Prefab UI
- **Frontend**: React 18, Vite 5, Tailwind CSS, Lucide, Framer Motion, Zustand, PDF.js, Playwright
- **Tooling**: uv, bun, just, ruff, pyright, Biome, pre-commit

## MCP tools

| Tool | Operations |
|------|-----------|
| `pdf_extract` | text, images, tables, metadata, fonts, links, outline |
| `pdf_manipulate` | merge, split, rotate, reorder, delete_pages, compress, encrypt, decrypt, optimize |
| `pdf_annotate` | watermark, stamp, highlight, underline, header_footer, page_numbers |
| `pdf_forms` | list_fields, fill, flatten, export_data |
| `pdf_convert` | to_markdown, to_images, to_html, from_html, from_markdown, from_images |
| `pdf_validate` | pdfa, structure, accessibility, integrity, compare |
| `pdf_rag` | chunk, index, search, list_documents, delete_index |
| `pdf_help` / `pdf_status` / `pdf_shutdown` | meta |

## Claude Desktop config

```json
{
  "mcpServers": {
    "pdf-mcp": {
      "command": "uv",
      "args": ["--directory", "D:\\Dev\\repos\\pdf-mcp", "run", "python", "run_server.py"]
    }
  }
}
```

For HTTP mode instead: `uv run python run_server.py --mode http --port 11131` and connect over `http://127.0.0.1:11131/mcp`.

## Configuration

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md). Key vars: `MCP_MODE` (stdio/http), `MCP_PORT` (11131), `FRONTEND_PORT` (11130), `RAG_STORE_PATH`, `UPLOAD_DIR`.

## Webapp

| Route | Page |
|-------|------|
| `/` | Dashboard (KPIs, LLM availability) |
| `/workbench` | PDF.js viewer + tool palette |
| `/pipeline` | Batch operations |
| `/chat` | LLM chat with RAG context |
| `/tools` / `/skills` / `/logs` | Discovery & logs |

## Documentation

- [Install & setup](docs/INSTALL.md)
- [Configuration](docs/CONFIGURATION.md)
- [Development](docs/DEVELOPMENT.md)
- [Tools & endpoints](docs/TOOLS.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Full LLM reference](llms-full.txt)
- [Changelog](CHANGELOG.md)

## License

MIT
