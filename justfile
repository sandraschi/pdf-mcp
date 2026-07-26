# pdf-mcp justfile
set positional-arguments := true

default: serve

# Start the server (dual transport — stdio or HTTP depending on env)
serve:
    uv run python run_server.py

# Start webapp dev server
dev: serve-webapp
    echo "Backend + frontend both running"

serve-webapp:
    cd webapp && bun run dev

# Lint
lint:
    uv run ruff check pdf_mcp/
    uv run ruff format pdf_mcp/ --check

# Format
fmt:
    uv run ruff check pdf_mcp/ --fix
    uv run ruff format pdf_mcp/

# Test
test:
    uv run pytest

# Typecheck webapp
tsc:
    cd webapp && npx tsc --noEmit

# E2E tests
e2e:
    cd webapp && npx playwright test

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
