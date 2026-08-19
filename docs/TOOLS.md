# Tools

pdf-mcp exposes 10 MCP tools. Each domain tool is a portmanteau: one tool name, one
`operation` parameter selecting the sub-operation.

## Tool surface

| Tool | Operations |
|------|-----------|
| `pdf_extract` | text, images, tables, metadata, fonts, links, outline |
| `pdf_manipulate` | merge, split, rotate, reorder, delete_pages, compress, encrypt, decrypt, optimize |
| `pdf_annotate` | watermark, stamp, highlight, underline, header_footer, page_numbers |
| `pdf_forms` | list_fields, fill, flatten, export_data |
| `pdf_convert` | to_markdown, to_images, to_html, from_html, from_markdown, from_images |
| `pdf_validate` | pdfa, structure, accessibility, integrity, compare |
| `pdf_rag` | chunk, index, search, list_documents, delete_index |
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
| `/api/jobs` | GET/POST | List / create batch jobs |
| `/api/jobs/{job_id}` | GET | Job status |
| `/api/pdf/{job_id}/result` | GET | Download job result file |
| `/api/logs` | GET | Ring-buffer log tail |
| `/mcp` | POST | MCP streamable HTTP transport |

Run `pdf_help` in any MCP client for per-tool input schemas.
