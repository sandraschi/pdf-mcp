set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

# pdf-mcp justfile

default: serve

# --- Start the server  dual transport  stdio or HTTP depending on env ---
serve:
    uv run python run_server.py

# Start backend + frontend (both) via the fleet launcher
dev:
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File start.ps1

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

# Build the Tauri NSIS installer (frontend + PyInstaller backend + bundle)
build-native:
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File src-tauri/build.ps1

# CUA pre-Tauri browser walk (start stack + nav walk in browser)
cua-webapp-test:
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/just/cua-webapp-test.ps1

# CUA-NSIS smoke test (install -> launch -> nav walk -> uninstall)
cua-nsis-test:
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/just/cua-nsis-test.ps1

# Package an MCPB bundle — fresh-stage source into mcpb/ first (MCPB_PACKAGING_STANDARDS.md §2.5)
mcpb-pack:
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/mcpb-pack.ps1
