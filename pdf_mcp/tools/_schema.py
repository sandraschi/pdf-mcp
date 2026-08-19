"""Shared explicit output schema for pdf-mcp tools (TOOL_DESIGN_STANDARDS.md §8)."""

TOOL_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean", "description": "Whether the operation succeeded"},
        "message": {"type": "string", "description": "Human-readable summary"},
    },
    "additionalProperties": True,
}
