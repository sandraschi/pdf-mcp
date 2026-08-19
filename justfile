set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

# pdf-mcp justfile

default: serve

# --- Start the server  dual transport  stdio or HTTP depending on env ---
serve:
    uv run python run_server.py

# Start webapp dev server
dev: serve-webapp
    echo "Backend + frontend both running"

serve-webapp:
    bun run --cwd webapp dev

# Lint
lint:
    uv run --extra dev ruff check pdf_mcp/
    uv run --extra dev ruff format pdf_mcp/ --check

# Format
fmt:
    uv run --extra dev ruff check pdf_mcp/ --fix
    uv run --extra dev ruff format pdf_mcp/

# Typecheck backend (fleet five-gate)
pyright:
    uv run --extra dev pyright pdf_mcp/

# Test
test:
    uv run --extra test pytest

# Typecheck webapp
tsc:
    bunx --cwd webapp tsc --noEmit

# E2E tests
e2e:
    bunx --cwd webapp playwright test

# Five-gate CI shape: ruff style, pyright + tsc types, pytest behavior
ci: lint pyright test tsc
    echo "All gates green"

# Sync deps
sync:
    uv sync

# Clean caches
clean:
    Remove-Item -Recurse -Force data/ -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force __pycache__/ -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force .venv/ -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force webapp/node_modules/ -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force webapp/dist/ -ErrorAction SilentlyContinue

# Bootstrap: install dev deps + pre-commit hook
bootstrap:
    uv sync --extra dev --extra test
    uv run pre-commit install
    bun install --cwd webapp
    Write-Host "Bootstrap complete: dev deps + pre-commit hooks + webapp deps installed." -ForegroundColor Green

# Package an MCPB bundle (requires @anthropic-ai/mcpb CLI)
mcpb-pack:
    npx @anthropic-ai/mcpb pack . dist/pdf-mcp-0.1.0.mcpb
