import logging
import os
import threading
import time
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from pdf_mcp.config import cfg
from pdf_mcp.server import mcp
from pdf_mcp.tools._schema import TOOL_OUTPUT_SCHEMA

logger = logging.getLogger("pdf-mcp")
_start_time = time.time()


@mcp.tool(output_schema=TOOL_OUTPUT_SCHEMA, app=True, annotations=ToolAnnotations(readOnlyHint=True))
async def pdf_help(
    tool_name: Annotated[str | None, Field(description="Name of a tool to get detailed help for. Lists all tools if omitted.")] = None,
) -> dict:
    """List available tools and get usage help for pdf-mcp.

    ## Return Format

    A dict with keys:
    - success: bool
    - message: str - human-readable summary
    - data: list of tools with name, description, and input schema, or detailed
      help for a single tool when tool_name is provided.

    ## Examples

    >>> await pdf_help()
    {"success": true, "message": "8 tools available.", "data": [{"name": "pdf_extract", ...}]}

    >>> await pdf_help(tool_name="pdf_extract")
    {"success": true, "message": "Help for pdf_extract.", "data": {...}}
    """
    try:
        tools = await mcp.list_tools()
        if tool_name:
            match = next((t for t in tools if t.name == tool_name), None)
            if not match:
                return {"success": False, "error": f"Tool not found: {tool_name}"}
            return {
                "success": True,
                "message": f"Help for {tool_name}.",
                "data": {
                    "name": match.name,
                    "description": match.description or "",
                    "inputSchema": getattr(match, "parameters", {}) or {},
                },
            }
        return {
            "success": True,
            "message": f"{len(tools)} tools available.",
            "data": [{"name": t.name, "description": t.description or ""} for t in tools],
        }
    except Exception as e:
        logger.exception("pdf_help failed: %s", e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


@mcp.tool(output_schema=TOOL_OUTPUT_SCHEMA, app=True, annotations=ToolAnnotations(readOnlyHint=True))
async def pdf_status() -> dict:
    """Report server status, version, uptime, and registered tool count.

    ## Return Format

    A dict with keys:
    - success: bool
    - server: str - server name
    - version: str - server version
    - uptime_seconds: int
    - tool_count: int
    - mode: str - stdio or http

    ## Examples

    >>> await pdf_status()
    {"success": true, "server": "pdf-mcp", "version": "0.1.0",
     "uptime_seconds": 42, "tool_count": 8, "mode": "http"}
    """
    try:
        tools = await mcp.list_tools()
        return {
            "success": True,
            "server": cfg.server_name,
            "version": cfg.version,
            "uptime_seconds": int(time.time() - _start_time),
            "tool_count": len(tools),
            "mode": cfg.mode,
        }
    except Exception as e:
        logger.exception("pdf_status failed: %s", e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


@mcp.tool(output_schema=TOOL_OUTPUT_SCHEMA, annotations=ToolAnnotations(destructiveHint=True))
async def pdf_shutdown(reason: Annotated[str | None, Field(description="Optional shutdown reason.")] = None) -> dict:
    """Gracefully shut down the pdf-mcp server.

    ## Return Format

    A dict with keys:
    - success: bool
    - message: str - shutdown confirmation

    ## Examples

    >>> await pdf_shutdown()
    {"success": true, "message": "Shutting down pdf-mcp."}
    """
    logger.warning("pdf_shutdown requested: %s", reason or "no reason given")
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return {"success": True, "message": "Shutting down pdf-mcp."}
