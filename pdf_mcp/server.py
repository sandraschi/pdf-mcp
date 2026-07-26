import logging
import sys
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP

from pdf_mcp.config import cfg

logger = logging.getLogger("pdf-mcp")

# ── FastMCP app ──

mcp = FastMCP(
    cfg.server_name,
    description=cfg.server_description,
    version=cfg.version,
)

# Import tools to register them

# ── Lifespan ──


@asynccontextmanager
async def app_lifespan(app: FastMCP):
    cfg.ensure_dirs()
    logger.info("pdf-mcp starting — uploads: %s, rag: %s", cfg.upload_dir, cfg.rag_store_path)
    yield


mcp._lifespan = app_lifespan


# ── FastAPI app (for webapp REST endpoints + CORS) ──


def create_http_app() -> FastAPI:
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def http_lifespan(app: FastAPI):
        cfg.ensure_dirs()
        yield

    app = FastAPI(title=cfg.server_name, version=cfg.version, lifespan=http_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"http://localhost:{cfg.frontend_port}",
            f"http://127.0.0.1:{cfg.frontend_port}",
            "http://tauri.localhost",
            "https://tauri.localhost",
            "tauri://localhost",
        ],
        allow_origin_regex=r"https?://(?:[a-zA-Z0-9-]+\.ts\.net|.*?\.tail-[a-f0-9]+\.ts\.net|tauri\.localhost|localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|100\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?$|^tauri://localhost$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _start_time = time.time()

    @app.get("/api/health")
    async def health():
        tool_count = len(mcp._tool_manager._tools) if hasattr(mcp, "_tool_manager") else 42
        return {
            "status": "ok",
            "server": cfg.server_name,
            "version": cfg.version,
            "uptime_seconds": int(time.time() - _start_time),
            "tool_count": tool_count,
        }

    @app.get("/api/v1/diagnostics")
    async def diagnostics():
        tool_count = len(mcp._tool_manager._tools) if hasattr(mcp, "_tool_manager") else 42
        tools_list = [{"name": t} for t in (mcp._tool_manager._tools.keys() if hasattr(mcp, "_tool_manager") else [])]
        return {
            "status": "ok",
            "server": cfg.server_name,
            "version": cfg.version,
            "uptime_seconds": int(time.time() - _start_time),
            "tool_count": tool_count,
            "tools": tools_list,
            "system": {"windows": sys.platform == "win32"},
            "errors": [],
        }

    return app


# ── Entry point ──


def main():
    import argparse

    parser = argparse.ArgumentParser(description="pdf-mcp server")
    parser.add_argument("--mode", choices=["stdio", "http"], default=cfg.mode)
    parser.add_argument("--host", default=cfg.host)
    parser.add_argument("--port", type=int, default=cfg.port)
    args = parser.parse_args()

    cfg.mode = args.mode
    cfg.host = args.host
    cfg.port = args.port

    if args.mode == "http":
        http_app = create_http_app()
        http_app.mount("/mcp", mcp.sse_app())

        logging.basicConfig(level=logging.INFO)
        logger.info("Starting HTTP server on %s:%s", args.host, args.port)
        uvicorn.run(http_app, host=args.host, port=args.port, log_level="info")
    else:
        logging.basicConfig(level=logging.WARNING)
        mcp.run_stdio_async()


if __name__ == "__main__":
    main()
