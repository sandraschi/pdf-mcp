import json
import logging
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from pdf_mcp.server import mcp
from pdf_mcp.services.llm import chat_completion

logger = logging.getLogger("pdf-mcp")

ALLOWED_TOOLS: dict[str, tuple[str, ...]] = {
    "pdf_extract": ("operation", "path", "pages"),
    "pdf_manipulate": ("operation", "path", "paths", "output_path", "pages", "angle", "new_order", "page_list", "quality", "password", "output_dir", "ranges"),
    "pdf_annotate": ("operation", "path", "output_path", "text", "image_path", "opacity", "position", "page", "x", "y", "search_text", "color", "header", "footer", "font_size", "start"),
    "pdf_forms": ("operation", "path", "output_path", "fields", "source", "text"),
    "pdf_convert": ("operation", "path", "output_path", "output_dir", "fmt", "dpi", "html", "markdown", "paths"),
    "pdf_validate": ("operation", "path", "path_a", "path_b"),
    "pdf_rag": ("operation", "path", "strategy", "chunk_size", "overlap", "query", "text", "limit", "doc_id"),
    "pdf_analyze": ("path",),
    "pdf_classify": ("path", "refine"),
    "pdf_export": ("path", "format", "include_summary"),
    "pdf_dedupe": ("paths", "threshold"),
}

MAX_STEPS = 6


async def _call_tool(name: str, args: dict) -> dict:
    if name not in ALLOWED_TOOLS:
        return {"success": False, "error": f"tool not allowed: {name}"}
    module_map = {
        "pdf_extract": "pdf_mcp.tools.extract",
        "pdf_manipulate": "pdf_mcp.tools.manipulate",
        "pdf_annotate": "pdf_mcp.tools.annotate",
        "pdf_forms": "pdf_mcp.tools.forms",
        "pdf_convert": "pdf_mcp.tools.convert",
        "pdf_validate": "pdf_mcp.tools.validate",
        "pdf_rag": "pdf_mcp.tools.rag",
        "pdf_analyze": "pdf_mcp.tools.intel",
        "pdf_classify": "pdf_mcp.tools.intel",
        "pdf_export": "pdf_mcp.tools.intel",
        "pdf_dedupe": "pdf_mcp.tools.intel",
    }
    import importlib

    module = importlib.import_module(module_map[name])
    fn = getattr(module, name)
    allowed = ALLOWED_TOOLS[name]
    kwargs = {k: v for k, v in (args or {}).items() if k in allowed and v is not None}
    result = await fn(**kwargs)
    return result


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True, idempotentHint=False))
async def pdf_do(
    task: Annotated[str, Field(description="Natural-language task to perform with the PDF tooling.")],
    path: Annotated[str | None, Field(description="Path to a PDF file if the task targets one.")] = None,
) -> dict:
    """Chain the PDF tools autonomously to complete a natural-language task.

    Requires a local LLM (Ollama or LM Studio). The LLM plans up to 6 tool calls
    from the pdf_* surface, the server executes them, and the LLM writes the final
    answer. pdf_do cannot call itself or pdf_shutdown.

    ## Return Format

    A dict with keys:
    - success: bool
    - answer: str - final natural-language answer
    - steps: list of {tool, args, result} execution records
    On failure: {success: False, error}.

    ## Examples

    >>> await pdf_do(task="Summarize this report and check it for PII.", path="report.pdf")
    {"success": true, "answer": "The report covers Q3 results... 3 PII hits found.",
     "steps": [{"tool": "pdf_export", ...}]}
    """
    try:
        if not path:
            return {"success": False, "error": "pdf_do needs a path to a PDF file."}
        allowed_desc = "\n".join(f"- {name}: {', '.join(params)}" for name, params in ALLOWED_TOOLS.items())
        plan_prompt = (
            "You are the planner for a PDF tool agent. Given a task and a PDF path, "
            "produce a JSON plan with up to 6 sequential steps. Each step: "
            '{"tool": "<allowed tool>", "args": {<param>: <value>}}. '
            "Use real PDF paths (the file exists). The path given may be reused for "
            "any step that needs a source file. Reply with JSON only, shape:\n"
            '{"steps": [...]}\n\nAllowed tools:\n' + allowed_desc
        )
        plan_reply = await chat_completion(
            [
                {"role": "system", "content": plan_prompt},
                {"role": "user", "content": f"Task: {task}\nPDF path: {path}"},
            ]
        )
        start, end = plan_reply.find("{"), plan_reply.rfind("}")
        if start == -1 or end == -1:
            return {"success": False, "error": "planner returned no JSON plan."}
        plan = json.loads(plan_reply[start : end + 1])
        steps = (plan or {}).get("steps") or []
        if len(steps) > MAX_STEPS:
            steps = steps[:MAX_STEPS]
        if not steps:
            return {"success": False, "error": "planner produced an empty plan."}

        records = []
        for step in steps:
            tool = (step or {}).get("tool", "")
            args = (step or {}).get("args") or {}
            if tool in ("pdf_do", "pdf_shutdown", "pdf_help", "pdf_status"):
                records.append({"tool": tool, "args": args, "result": {"success": False, "error": f"tool not allowed: {tool}"}})
                continue
            if not path and tool != "pdf_dedupe":
                records.append({"tool": tool, "args": args, "result": {"success": False, "error": "no source path available"}})
                continue
            if "path" in ALLOWED_TOOLS.get(tool, ()) and not args.get("path"):
                args["path"] = path
            try:
                result = await _call_tool(tool, args)
            except Exception as e:
                logger.exception("pdf_do step %s failed: %s", tool, e)
                result = {"success": False, "error": str(e)}
            records.append({"tool": tool, "args": args, "result": result})
            if not result.get("success"):
                break

        transcript = "\n".join(f"step {i + 1} {r['tool']}({json.dumps(r['args'], ensure_ascii=False)}): {json.dumps(r['result'], ensure_ascii=False)[:600]}" for i, r in enumerate(records))
        answer = await chat_completion(
            [
                {"role": "system", "content": "You are the pdf-mcp agent. Summarize what was done and the outcome for the user, in 2-4 sentences. Be concrete; mention numbers and file paths."},
                {"role": "user", "content": f"Task: {task}\n\nExecution transcript:\n{transcript}"},
            ]
        )
        return {
            "success": True,
            "answer": answer,
            "steps": [{"tool": r["tool"], "args": r["args"], "result": r["result"]} for r in records],
            "message": f"Completed '{task}' in {len(records)} step(s).",
        }
    except Exception as e:
        logger.exception("pdf_do failed: %s", e)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
