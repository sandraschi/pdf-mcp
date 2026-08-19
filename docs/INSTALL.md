# Install

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager + runtime)
- [Bun](https://bun.sh) (webapp frontend)
- Optional: [just](https://github.com/casey/just) for task recipes

## Windows

```powershell
git clone https://github.com/sandraschi/pdf-mcp
cd pdf-mcp
uv sync
Copy-Item .env.example .env
.\start.ps1
```

`start.ps1` clears zombie ports, waits for backend readiness, and auto-opens the
dashboard at http://127.0.0.1:11130.

## MCP client (stdio)

Add to your MCP client config:

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

## HTTP mode

```powershell
uv run python run_server.py --mode http --host 127.0.0.1 --port 11131
```

- REST + MCP (streamable HTTP): `http://127.0.0.1:11131`
- Health: `http://127.0.0.1:11131/api/health`

## Upgrade

```powershell
git pull
uv sync
cd webapp && bun install
```

## Uninstall

```powershell
Remove-Item -Recurse -Force .venv, data, webapp/node_modules
```

Note: `data/` holds uploaded files and the LanceDB index. Delete it to reset all state.
