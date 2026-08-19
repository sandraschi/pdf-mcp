# Tools

pdf-mcp exposes 16 MCP tools. Each domain tool is a portmanteau: one tool name, one
`operation` parameter selecting the sub-operation.

## Tool surface

| Tool | Operations |
|------|-----------|
| `pdf_extract` | text, images, tables, metadata, fonts, links, outline |
| `pdf_manipulate` | merge, split, rotate, reorder, delete_pages, compress, encrypt, decrypt, optimize |
| `pdf_annotate` | watermark, stamp, highlight, underline, header_footer, page_numbers, summary_box |
| `pdf_forms` | list_fields, fill, flatten, export_data, auto_fill |
| `pdf_convert` | to_markdown, to_images, to_html, from_html, from_markdown, from_images |
| `pdf_validate` | pdfa, structure, accessibility, integrity, compare |
| `pdf_rag` | chunk, index, search, similar, synthesize, list_documents, delete_index |
| `pdf_analyze` | scanned/digital detection + layout stats |
| `pdf_redact` | blacken terms + PII |
| `pdf_classify` | document-type classifier |
| `pdf_dedupe` | exact/near-duplicate detection |
| `pdf_export` | document brief (markdown/json) |
| `pdf_do` | agentic chaining (requires local LLM) |
| `pdf_help` | — list tools or get help for one tool |
| `pdf_status` | — server status, version, uptime, tool count |
| `pdf_shutdown` | — gracefully stop the server |

## Example

```json
{
  "name": "pdf_extract",
  "arguments": {
    "operation": "text",
    "path": "C:\\data\\report.pdf",
    "pages": "1-5"
  }
}
```

## REST endpoints (webapp + IDE)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Liveness, version, uptime, tool count |
| `/api/v1/diagnostics` | GET | Tool list, system info, errors |
| `/api/tools` | GET | Tool list with input schemas |
| `/api/skills` | GET | Skill list |
| `/api/skills/{name}` | GET | Raw SKILL.md content |
| `/api/llm/discover` | GET | Ollama / LM Studio detection |
| `/api/chat` | POST | LLM chat completion |
| `/api/pdf/upload` | POST | Multipart PDF upload |
| `/api/jobs` | GET/POST | List / create batch jobs (also accepts `recipe`) |
| `/api/jobs/{job_id}` | GET | Job status (incl. recipe steps) |
| `/api/pdf/{job_id}/result` | GET | Download job result file |
| `/api/logs` | GET | Ring-buffer log tail |
| `/api/recipes` | GET | Named pipeline recipes |
| `/api/pdf/analyze` | GET | OCR readiness for an uploaded file |
| `/api/pdf/compare` | POST | Side-by-side text diff |
| `/api/pdf/dedupe` | POST | Duplicate detection |
| `/api/rag/search` | POST | Synchronous RAG search |
| `/api/share/{job_id}` | POST | 24 h share link for a completed job |
| `/api/share/{token}` | GET | Stream a shared result |
| `/api/stats` | GET | Per-operation usage stats |
| `/api/watch/status` | GET | Watch-folder status |
| `/mcp` | POST | MCP streamable HTTP transport |

## Pipelines

`POST /api/jobs` with `{"recipe": "ingest"|"redact_export"|"brief", "params": {...}}`
runs a multi-step recipe: ingest = analyze → index → brief; redact_export = analyze →
redact(pii) → brief. Drop PDFs into `data/watch/` and the server runs `ingest` automatically.

Run `pdf_help` in any MCP client for per-tool input schemas.
