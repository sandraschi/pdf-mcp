# Configuration

pdf-mcp is configured through environment variables read at startup (`pdf_mcp/config.py`).

## Quick start

```powershell
Copy-Item .env.example .env
# edit .env as needed, then:
.\start.ps1
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_MODE` | `stdio` | Server mode: `stdio` (Claude Desktop / Cursor) or `http` |
| `MCP_HOST` | `127.0.0.1` | HTTP bind host |
| `MCP_PORT` | `11131` | HTTP port (backend) |
| `FRONTEND_PORT` | `11130` | Frontend dev-server port (CORS origin) |
| `UPLOAD_DIR` | `data/uploads` | Directory for uploaded and generated PDFs |
| `RAG_STORE_PATH` | `data/lancedb` | LanceDB vector store path |
| `RAG_EMBEDDING_URL` | *(empty)* | OpenAI-compatible embedding endpoint (e.g. Ollama `/v1/embeddings`) |
| `RAG_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Embedding model name |
| `PDF_MCP_TAURI` | *(empty)* | Set to `1` when running inside a Tauri WebView |

## RAG embeddings

With `RAG_EMBEDDING_URL` empty, indexing falls back to deterministic
hash-based vectors (no external model download). To use semantic embeddings,
point at a local endpoint:

```dotenv
RAG_EMBEDDING_URL=http://127.0.0.1:11434/v1/embeddings
RAG_EMBEDDING_MODEL=nomic-embed-text
```

## CORS

The HTTP app allows origins from `localhost`, `127.0.0.1`, the configured
frontend port, Tailscale (`.ts.net`, `tail-*.ts.net`), LAN ranges, and the Tauri
WebView origins (`tauri://localhost`, `http(s)://tauri.localhost`). No further
configuration required for local development.
