import asyncio
import logging
import secrets
import sys
import threading
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response

from pdf_mcp.config import cfg
from pdf_mcp.services.llm import chat_completion as _llm_chat_completion
from pdf_mcp.services.llm import default_provider as _llm_default_provider
from pdf_mcp.services.llm import discover_providers as _llm_discover_providers

logger = logging.getLogger("pdf-mcp")

# ── FastMCP app ──


async def _sampling_handler(messages, params, ctx) -> str:
    """Server-side sampling fallback routed to the local LLM (Ollama / LM Studio)."""
    from pdf_mcp.services.llm import chat_completion

    texts = []
    for m in messages or []:
        role = getattr(m, "role", "user")
        content = getattr(m, "content", "")
        if not isinstance(content, str):
            content = getattr(content, "text", str(content))
        texts.append(f"{role}: {content}")
    prompt = "\n".join(texts) if texts else ""
    system = getattr(params, "instructions", None) or getattr(params, "system_prompt", None)
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    try:
        return await chat_completion(msgs)
    except Exception:
        provider, model, _ = await _llm_default_provider()
        if not provider:
            return "No local LLM available for sampling. Start Ollama or LM Studio."
        raise


mcp = FastMCP(
    cfg.server_name,
    instructions=cfg.server_description,
    version=cfg.version,
    providers=[SkillsDirectoryProvider(roots=str(Path(__file__).resolve().parent / "skills"))],
    sampling_handler=_sampling_handler,
    sampling_handler_behavior="fallback",
)


# ── Log ring buffer (for /api/logs) ──


class LogRingHandler(logging.Handler):
    def __init__(self, capacity: int = 500):
        super().__init__()
        self.capacity = capacity
        self.buffer: deque[dict] = deque(maxlen=capacity)
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            ts = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
            self.buffer.append(
                {
                    "timestamp": ts,
                    "level": record.levelname.lower(),
                    "source": record.name,
                    "message": self.format(record).split(" ", 3)[-1] if record.exc_info else record.getMessage(),
                }
            )
        except Exception:
            pass


_log_ring = LogRingHandler()


# ── Job store (in-memory batch executor) ──


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._uploads: dict[str, str] = {}

    async def upload(self, filename: str, data: bytes) -> dict:
        cfg.upload_dir.mkdir(parents=True, exist_ok=True)
        safe = Path(filename).name
        path = cfg.upload_dir / f"{uuid4().hex[:12]}_{safe}"
        path.write_bytes(data)
        self._uploads[safe] = str(path)
        pages = self._count_pages(str(path))
        return {"job_id": uuid4().hex[:12], "pages": pages, "size": len(data), "path": str(path)}

    @staticmethod
    def _count_pages(path: str) -> int:
        try:
            import fitz

            doc = fitz.open(path)
            try:
                return len(doc)
            finally:
                doc.close()
        except Exception:
            return 0

    def list_uploads(self) -> dict[str, str]:
        return dict(self._uploads)

    def register_upload(self, filename: str, path: str) -> None:
        self._uploads[Path(filename).name] = str(path)

    def create_job(self, operation: str, params: dict, steps: list[dict] | None = None) -> str:
        job_id = uuid4().hex[:12]
        self._jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "operation": operation,
            "params": params,
            "created": datetime.now(UTC).isoformat(),
            "result_path": None,
            "error": None,
            "steps": steps,
            "step_index": 0,
            "step_log": [],
        }
        return job_id

    def get_job(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[dict]:
        return [
            {
                "job_id": j["job_id"],
                "operation": j["operation"],
                "status": j["status"],
                "created": j["created"],
                "steps": len(j["steps"]) if j.get("steps") else None,
            }
            for j in self._jobs.values()
        ]

    def mark_running(self, job_id: str) -> None:
        self._jobs[job_id]["status"] = "running"

    def set_step(self, job_id: str, index: int) -> None:
        job = self._jobs[job_id]
        job["step_index"] = index
        if job.get("steps"):
            job["step_log"].append({"step": index, "operation": job["steps"][index]["operation"], "status": "running"})

    def append_step_result(self, job_id: str, result: dict) -> None:
        log = self._jobs[job_id]["step_log"]
        if log:
            log[-1]["status"] = "done" if result.get("success") else "failed"
            log[-1]["detail"] = result.get("message") or result.get("error")

    def mark_done(self, job_id: str, result_path: str | None, error: str | None = None) -> None:
        job = self._jobs[job_id]
        job["status"] = "failed" if error else "completed"
        job["result_path"] = result_path
        job["error"] = error


jobs = JobStore()


# ── LLM discovery + chat ──

_PERSONALITY_PROMPTS: dict[str, str] = {
    "research-assistant": "You are a precise research assistant. Answer concisely and cite sources when possible.",
    "expert-reviewer": "You are a critical expert reviewer. Evaluate claims rigorously and flag weaknesses.",
    "quick-summarizer": "You are a quick summarizer. Return short, structured summaries.",
    "technical-writer": "You are a technical writer. Produce clear, well-structured technical prose.",
}


async def _discover_providers() -> dict[str, dict]:
    return await _llm_discover_providers()


async def _chat_completion(messages: list[dict], provider: str | None, model: str | None) -> str:
    provider, model, _ = await _llm_default_provider()
    if not provider or not model:
        raise RuntimeError("No local LLM detected.")
    return await _llm_chat_completion(messages, provider, model)


# ── Usage stats registry ──


class StatsRegistry:
    def __init__(self) -> None:
        self._ops: dict[str, dict] = {}
        self._total_jobs = 0
        self._total_files = 0

    def record(self, operation: str, elapsed_ms: float) -> None:
        op = self._ops.setdefault(operation, {"count": 0, "total_ms": 0.0, "last_at": None})
        op["count"] += 1
        op["total_ms"] += elapsed_ms
        op["last_at"] = datetime.now(UTC).isoformat()
        self._total_jobs += 1

    def add_file(self) -> None:
        self._total_files += 1

    def snapshot(self) -> dict:
        ops = []
        for name, op in sorted(self._ops.items(), key=lambda kv: -kv[1]["count"]):
            ops.append(
                {
                    "operation": name,
                    "count": op["count"],
                    "avg_ms": round(op["total_ms"] / op["count"], 1) if op["count"] else 0,
                    "last_at": op["last_at"],
                }
            )
        return {"operations": ops, "total_jobs": self._total_jobs, "total_files": self._total_files}


stats = StatsRegistry()


# ── Share registry (tokenized result links) ──

_share_expiry_s = 86400  # 24 h


class ShareRegistry:
    def __init__(self) -> None:
        self._links: dict[str, dict] = {}

    def create(self, job_id: str) -> str:
        token = secrets.token_urlsafe(16)
        self._links[token] = {"job_id": job_id, "expires": time.time() + _share_expiry_s}
        return token

    def resolve(self, token: str) -> str | None:
        link = self._links.get(token)
        if not link:
            return None
        if time.time() > link["expires"]:
            self._links.pop(token, None)
            return None
        return link["job_id"]


shares = ShareRegistry()


# ── Pipeline recipes ──


RECIPES: dict[str, list[dict]] = {
    "ingest": [
        {"operation": "analyze", "params": {}},
        {"operation": "index", "params": {}},
        {"operation": "export_brief", "params": {"include_summary": True}},
    ],
    "redact_export": [
        {"operation": "analyze", "params": {}},
        {"operation": "redact", "params": {"pii": True}},
        {"operation": "export_brief", "params": {"include_summary": False}},
    ],
    "brief": [
        {"operation": "export_brief", "params": {"include_summary": True}},
    ],
}


def _recipe_steps(recipe: str) -> list[dict] | None:
    return RECIPES.get(recipe)


# ── Watch-folder auto-process ──

watch_state: dict[str, Any] = {"watching": False, "processed": [], "errors": []}


async def _watch_loop() -> None:
    watch_dir = cfg.repo_root / "data" / "watch"
    watch_dir.mkdir(parents=True, exist_ok=True)
    watch_state["watching"] = True
    seen: set[str] = set()
    while True:
        try:
            for p in sorted(watch_dir.glob("*.pdf")):
                if p.name in seen:
                    continue
                seen.add(p.name)
                try:
                    jobs.register_upload(p.name, str(p))
                    job_id = jobs.create_job("ingest", {"filename": p.name}, steps=_recipe_steps("ingest"))
                    asyncio.create_task(_execute_recipe(job_id, "ingest", _recipe_steps("ingest") or [], {"filename": p.name}))
                    stats.add_file()
                    watch_state["processed"].append({"file": p.name, "job_id": job_id, "at": datetime.now(UTC).isoformat()})
                    watch_state["processed"] = watch_state["processed"][-50:]
                    logger.info("watch-folder: processing %s", p.name)
                except Exception as e:
                    watch_state["errors"].append({"file": p.name, "error": str(e)})
                    watch_state["errors"] = watch_state["errors"][-50:]
        except Exception:
            logger.exception("watch loop error")
        await asyncio.sleep(5)


# ── Operation → tool dispatch for the batch job executor ──


async def _run_operation(operation: str, params: dict) -> dict:
    """Dispatch a batch operation to the matching portmanteau tool."""
    from pdf_mcp.tools.annotate import pdf_annotate
    from pdf_mcp.tools.convert import pdf_convert
    from pdf_mcp.tools.extract import pdf_extract
    from pdf_mcp.tools.forms import pdf_forms
    from pdf_mcp.tools.manipulate import pdf_manipulate
    from pdf_mcp.tools.rag import pdf_rag
    from pdf_mcp.tools.validate import pdf_validate

    filename = params.get("filename") or params.get("path")
    uploads = jobs.list_uploads()
    path: str | None = uploads.get(str(filename)) if filename else None
    path = path or (params.get("path") if isinstance(params.get("path"), str) else None)

    def _fail(msg: str) -> dict:
        return {"success": False, "error": msg}

    if not path and operation not in ("merge", "search", "list_documents"):
        return _fail("No source file found. Upload a PDF first (POST /api/pdf/upload).")

    if operation in ("extract_text", "extract_images", "extract_tables"):
        from pdf_mcp.models import PdfExtractOperation

        return await pdf_extract(operation=cast(PdfExtractOperation, operation.removeprefix("extract_")), path=path or "")
    if operation in ("compress", "rotate", "encrypt", "decrypt", "optimize", "delete_pages", "reorder"):
        return await pdf_manipulate(
            operation=operation,
            path=path or "",
            angle=int(params.get("angle", 90)),
            password=params.get("password") or "",
            new_order=params.get("new_order") or [],
            page_list=params.get("page_list") or [],
        )
    if operation == "merge":
        return await pdf_manipulate(operation="merge", path=path or "", paths=params.get("paths") or [])
    if operation == "split":
        return await pdf_manipulate(operation="split", path=path or "", output_dir=str(cfg.upload_dir / "split"))
    if operation == "convert_markdown":
        return await pdf_convert(operation="to_markdown", path=path or "")
    if operation in ("watermark", "stamp", "highlight", "underline", "header_footer", "page_numbers", "summary_box"):
        return await pdf_annotate(operation=operation, path=path or "", text=params.get("text"))
    if operation in ("list_fields", "fill", "flatten", "export_data", "auto_fill"):
        return await pdf_forms(operation=operation, path=path or "", fields=params.get("fields"), source=params.get("source"), text=params.get("text"))
    if operation in ("pdfa", "structure", "accessibility", "integrity", "compare"):
        return await pdf_validate(operation=operation, path=path or "", path_a=params.get("path_a"), path_b=params.get("path_b"))
    if operation in ("chunk", "index", "search", "similar", "synthesize", "list_documents", "delete_index"):
        return await pdf_rag(
            operation=operation,
            path=path,
            query=params.get("query"),
            text=params.get("text"),
            limit=int(params.get("limit", 10)),
            doc_id=params.get("doc_id"),
        )
    if operation == "analyze":
        from pdf_mcp.tools.intel import pdf_analyze

        return await pdf_analyze(path=path or "")
    if operation == "redact":
        from pdf_mcp.tools.intel import pdf_redact

        return await pdf_redact(path=path or "", pii=bool(params.get("pii", False)), terms=params.get("terms"))
    if operation == "classify":
        from pdf_mcp.tools.intel import pdf_classify

        return await pdf_classify(path=path or "")
    if operation == "dedupe":
        from pdf_mcp.tools.intel import pdf_dedupe

        return await pdf_dedupe(paths=params.get("paths") or [path] if path else (params.get("paths") or []))
    if operation == "export_brief":
        from pdf_mcp.tools.intel import pdf_export

        return await pdf_export(path=path or "", format=params.get("format", "markdown"), include_summary=bool(params.get("include_summary", True)))
    if operation == "do":
        from pdf_mcp.tools.agent import pdf_do

        return await pdf_do(task=params.get("task", ""), path=path)
    return {"success": False, "error": f"Unknown operation: {operation}"}


async def _execute_job(job_id: str, operation: str, params: dict) -> None:
    jobs.mark_running(job_id)
    start = time.time()
    try:
        result = await _run_operation(operation, params)
        stats.record(operation, (time.time() - start) * 1000)
        if result.get("success"):
            result_path = result.get("path") or (result.get("files") or [None])[0]
            jobs.mark_done(job_id, result_path)
        else:
            jobs.mark_done(job_id, None, result.get("error", "operation failed"))
    except Exception as e:
        stats.record(operation, (time.time() - start) * 1000)
        logger.exception("job %s failed: %s", job_id, e)
        jobs.mark_done(job_id, None, str(e))


async def _execute_recipe(job_id: str, recipe: str, steps: list[dict], base_params: dict) -> None:
    jobs.mark_running(job_id)
    for idx, step in enumerate(steps):
        jobs.set_step(job_id, idx)
        start = time.time()
        try:
            op_params = {**base_params, **step.get("params", {})}
            result = await _run_operation(step["operation"], op_params)
            stats.record(step["operation"], (time.time() - start) * 1000)
            jobs.append_step_result(job_id, result)
            if not result.get("success"):
                jobs.mark_done(job_id, None, f"{step['operation']} failed: {result.get('error')}")
                return
            if idx == len(steps) - 1:
                result_path = result.get("path") or (result.get("files") or [None])[0]
                jobs.mark_done(job_id, result_path)
        except Exception as e:
            stats.record(step["operation"], (time.time() - start) * 1000)
            logger.exception("recipe %s step %d failed: %s", recipe, idx, e)
            jobs.mark_done(job_id, None, str(e))
            return


# ── HTTP app: FastMCP's Starlette app + webapp REST endpoints ──


def create_http_app():
    cfg.ensure_dirs()
    app = mcp.http_app()

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

    def _tool_json(tool) -> dict:
        schema = getattr(tool, "parameters", {}) or {}
        return {"name": tool.name, "description": tool.description or "", "inputSchema": schema}

    async def health(request: Request) -> JSONResponse:
        tools = await mcp.list_tools()
        return JSONResponse(
            {
                "status": "ok",
                "server": cfg.server_name,
                "version": cfg.version,
                "uptime_seconds": int(time.time() - _start_time),
                "tool_count": len(tools),
            }
        )

    async def diagnostics(request: Request) -> JSONResponse:
        tools = await mcp.list_tools()
        return JSONResponse(
            {
                "status": "ok",
                "server": cfg.server_name,
                "version": cfg.version,
                "uptime_seconds": int(time.time() - _start_time),
                "tool_count": len(tools),
                "tools": [{"name": t.name} for t in tools],
                "system": {"windows": sys.platform == "win32"},
                "errors": [],
            }
        )

    async def list_tools(request: Request) -> JSONResponse:
        tools = await mcp.list_tools()
        return JSONResponse([_tool_json(t) for t in tools])

    async def list_skills(request: Request) -> JSONResponse:
        skills_dir = Path(__file__).resolve().parent / "skills"
        skills = []
        if skills_dir.exists():
            for skill_dir in sorted(skills_dir.iterdir()):
                if not skill_dir.is_dir():
                    continue
                md = skill_dir / "SKILL.md"
                description = ""
                if md.exists():
                    content = md.read_text(encoding="utf-8")
                    for line in content.splitlines():
                        if line.startswith("description"):
                            description = line.split(":", 1)[-1].strip()
                            break
                skills.append({"name": skill_dir.name, "description": description})
        return JSONResponse(skills)

    async def get_skill(request: Request) -> Response:
        name = request.path_params.get("name", "")
        skill_md = Path(__file__).resolve().parent / "skills" / name / "SKILL.md"
        if not skill_md.exists():
            return JSONResponse({"error": "Skill not found"}, status_code=404)
        return PlainTextResponse(skill_md.read_text(encoding="utf-8"))

    async def llm_discover(request: Request) -> JSONResponse:
        providers = await _discover_providers()
        return JSONResponse(
            {
                "providers": providers,
                "default_provider": next((k for k, v in providers.items() if v["available"]), None),
            }
        )

    async def chat(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse({"content": "Invalid JSON payload."}, status_code=400)
        messages = payload.get("messages") or []
        personality = payload.get("personality", "research-assistant")
        provider = payload.get("provider")
        model = payload.get("model")

        providers = await _discover_providers()
        if not provider:
            provider = next((k for k, v in providers.items() if v["available"]), None)
        if not provider or not providers.get(provider, {}).get("available"):
            return JSONResponse(
                {"content": ("No local LLM detected. Start Ollama (127.0.0.1:11434) or LM Studio (127.0.0.1:1234) to enable AI chat. The rest of the PDF tooling works without an LLM.")}
            )
        system_prompt = _PERSONALITY_PROMPTS.get(personality, _PERSONALITY_PROMPTS["research-assistant"])
        if not model:
            models = providers[provider].get("models") or []
            model = models[0] if models else "llama3"
        try:
            content = await _chat_completion([{"role": "system", "content": system_prompt}, *messages], provider, model)
            return JSONResponse({"content": content})
        except Exception as e:
            logger.exception("chat completion failed: %s", e)
            return JSONResponse({"content": f"Chat failed: {e}"})

    async def upload_pdf(request: Request) -> JSONResponse:
        from starlette.datastructures import UploadFile as StarletteUploadFile

        form = await request.form()
        file = form.get("file")
        if not isinstance(file, StarletteUploadFile):
            return JSONResponse({"error": "file field required"}, status_code=400)
        data = await file.read()
        result = await jobs.upload(file.filename or "upload.pdf", data)
        stats.add_file()
        return JSONResponse({"job_id": result["job_id"], "pages": result["pages"], "size": result["size"]})

    async def list_jobs(request: Request) -> JSONResponse:
        return JSONResponse(jobs.list_jobs())

    async def create_job(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON payload."}, status_code=400)
        operation = payload.get("operation") or ""
        recipe = payload.get("recipe") or ""
        params = payload.get("params") or {}
        if recipe:
            steps = _recipe_steps(recipe)
            if not steps:
                return JSONResponse({"error": f"unknown recipe: {recipe}"}, status_code=400)
            job_id = jobs.create_job(f"recipe:{recipe}", params, steps=steps)
            asyncio.create_task(_execute_recipe(job_id, recipe, steps, params))
            return JSONResponse({"job_id": job_id})
        if not operation:
            return JSONResponse({"error": "operation required"}, status_code=400)
        job_id = jobs.create_job(operation, params)
        asyncio.create_task(_execute_job(job_id, operation, params))
        return JSONResponse({"job_id": job_id})

    async def get_job(request: Request) -> JSONResponse:
        job = jobs.get_job(request.path_params.get("job_id", ""))
        if not job:
            return JSONResponse({"error": "Job not found"}, status_code=404)
        return JSONResponse(job)

    async def job_result(request: Request) -> FileResponse | JSONResponse:
        job = jobs.get_job(request.path_params.get("job_id", ""))
        if not job:
            return JSONResponse({"error": "Job not found"}, status_code=404)
        if job["status"] != "completed" or not job["result_path"]:
            return JSONResponse({"error": "Job not completed"}, status_code=409)
        path = Path(job["result_path"])
        if not path.exists():
            return JSONResponse({"error": "Result file missing"}, status_code=404)
        return FileResponse(path, filename=path.name)

    async def get_logs(request: Request) -> JSONResponse:
        query = request.query_params
        level = query.get("level")
        search = query.get("search")
        try:
            limit = int(query.get("limit", "100"))
        except ValueError:
            limit = 100
        entries = list(_log_ring.buffer)
        if level and level != "all":
            entries = [e for e in entries if e["level"] == level]
        if search:
            entries = [e for e in entries if search.lower() in e["message"].lower()]
        return JSONResponse(entries[-limit:])

    async def get_uploaded_file(request: Request) -> FileResponse | JSONResponse:
        name = request.path_params.get("name", "")
        path = jobs.list_uploads().get(name)
        if not path or not Path(path).exists():
            return JSONResponse({"error": "File not found"}, status_code=404)
        return FileResponse(path, filename=name)

    async def rag_search(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON payload."}, status_code=400)
        from pdf_mcp.tools.rag import pdf_rag

        result = await pdf_rag(operation="search", query=payload.get("query", ""), limit=int(payload.get("limit", 10)))
        return JSONResponse(result)

    async def analyze_file(request: Request) -> JSONResponse:
        from pdf_mcp.tools.intel import pdf_analyze

        name = request.query_params.get("filename", "")
        path = jobs.list_uploads().get(name)
        if not path:
            return JSONResponse({"error": "File not found"}, status_code=404)
        result = await pdf_analyze(path=path)
        return JSONResponse({**result, "filename": name})

    async def compare_files(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON payload."}, status_code=400)
        uploads = jobs.list_uploads()
        path_a = uploads.get(payload.get("path_a", ""))
        path_b = uploads.get(payload.get("path_b", ""))
        if not path_a or not path_b:
            return JSONResponse({"error": "Both files must be uploaded first."}, status_code=400)
        from pdf_mcp.tools.validate import pdf_validate

        result = await pdf_validate(operation="compare", path=path_a, path_a=path_a, path_b=path_b)
        return JSONResponse(result)

    async def dedupe_files(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON payload."}, status_code=400)
        uploads = jobs.list_uploads()
        names = payload.get("filenames") or []
        paths = [uploads[n] for n in names if n in uploads]
        if not paths:
            return JSONResponse({"error": "No matching uploaded files."}, status_code=400)
        from pdf_mcp.tools.intel import pdf_dedupe

        result = await pdf_dedupe(paths=paths, threshold=float(payload.get("threshold", 0.85)))
        return JSONResponse(result)

    async def list_recipes(request: Request) -> JSONResponse:
        return JSONResponse({"recipes": [{"name": name, "steps": [s["operation"] for s in steps]} for name, steps in RECIPES.items()]})

    async def create_share(request: Request) -> JSONResponse:
        job = jobs.get_job(request.path_params.get("job_id", ""))
        if not job or job["status"] != "completed" or not job["result_path"]:
            return JSONResponse({"error": "Job not completed"}, status_code=409)
        token = shares.create(job["job_id"])
        return JSONResponse({"url": f"/api/share/{token}"})

    async def resolve_share(request: Request) -> FileResponse | JSONResponse:
        token = request.path_params.get("token", "")
        job_id = shares.resolve(token)
        if not job_id:
            return JSONResponse({"error": "Share link expired or not found"}, status_code=410)
        job = jobs.get_job(job_id)
        if not job or not job["result_path"]:
            return JSONResponse({"error": "Job result missing"}, status_code=404)
        path = Path(job["result_path"])
        if not path.exists():
            return JSONResponse({"error": "Result file missing"}, status_code=404)
        return FileResponse(path, filename=path.name)

    async def get_stats(request: Request) -> JSONResponse:
        return JSONResponse(stats.snapshot())

    async def watch_status(request: Request) -> JSONResponse:
        return JSONResponse(watch_state)

    app.add_route("/api/health", health)
    app.add_route("/api/v1/diagnostics", diagnostics)
    app.add_route("/api/tools", list_tools)
    app.add_route("/api/skills", list_skills)
    app.add_route("/api/skills/{name}", get_skill)
    app.add_route("/api/llm/discover", llm_discover)
    app.add_route("/api/chat", chat, methods=["POST"])
    app.add_route("/api/pdf/upload", upload_pdf, methods=["POST"])
    app.add_route("/api/pdf/files/{name}", get_uploaded_file)
    app.add_route("/api/pdf/analyze", analyze_file)
    app.add_route("/api/pdf/compare", compare_files, methods=["POST"])
    app.add_route("/api/pdf/dedupe", dedupe_files, methods=["POST"])
    app.add_route("/api/rag/search", rag_search, methods=["POST"])
    app.add_route("/api/recipes", list_recipes)
    app.add_route("/api/share/{job_id}", create_share, methods=["POST"])
    app.add_route("/api/share/{token}", resolve_share)
    app.add_route("/api/stats", get_stats)
    app.add_route("/api/watch/status", watch_status)
    app.add_route("/api/jobs", list_jobs)
    app.add_route("/api/jobs", create_job, methods=["POST"])
    app.add_route("/api/jobs/{job_id}", get_job)
    app.add_route("/api/pdf/{job_id}/result", job_result)
    app.add_route("/api/logs", get_logs)

    return app


# ── Entry point ──


def main():
    import argparse

    import pdf_mcp.tools  # noqa: F401 — imports all tool modules to register tools

    parser = argparse.ArgumentParser(description="pdf-mcp server")
    parser.add_argument("--mode", choices=["stdio", "http"], default=cfg.mode)
    parser.add_argument("--host", default=cfg.host)
    parser.add_argument("--port", type=int, default=cfg.port)
    args = parser.parse_args()

    cfg.mode = args.mode
    cfg.host = args.host
    cfg.port = args.port

    logging.basicConfig(level=logging.INFO)
    logging.getLogger("pdf-mcp").addHandler(_log_ring)

    if args.mode == "http":
        threading.Thread(target=lambda: asyncio.run(_watch_loop()), daemon=True).start()
        http_app = create_http_app()

        logger.info("Starting HTTP server on %s:%s", args.host, args.port)
        uvicorn.run(http_app, host=args.host, port=args.port, log_level="info")
    else:
        logging.getLogger("pdf-mcp").setLevel(logging.INFO)
        asyncio.run(mcp.run_stdio_async())


if __name__ == "__main__":
    main()
