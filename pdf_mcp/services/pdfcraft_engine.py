"""PdfCraft headless engine adapter (Lane A).

Wraps the installed commercial PdfCraft CLI
(`C:\\Program Files\\PdfCraft\\pdfcraft-cli.exe`, env `PDFCRAFT_CLI`)
as a subprocess. No MCP lifecycle, no live-app control port.

Doctrine: wrap, don't reimplement. Python keeps RAG/forms/classify;
render/combine/split/edit/OCR/optimize/audit delegate here.
All writes land in the job outbox (`data/pdfcraft/`), never in place.

Error taxonomy (declared, never mocked):
- wrappee_missing: CLI binary not found
- engine_error: CLI exited nonzero (stderr surfaced)
- engine_timeout: CLI exceeded timeout
"""

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger("pdf-mcp")

DEFAULT_CLI = r"C:\Program Files\PdfCraft\pdfcraft-cli.exe"


def cli_path() -> Path:
    return Path(os.getenv("PDFCRAFT_CLI", DEFAULT_CLI))


def is_enabled() -> bool:
    return os.getenv("PDFCRAFT_ENABLED", "1").lower() not in ("0", "false", "no")


def outbox_dir() -> Path:
    root = Path(__file__).resolve().parent.parent.parent
    box = Path(os.getenv("PDFCRAFT_OUTBOX", str(root / "data" / "pdfcraft")))
    box.mkdir(parents=True, exist_ok=True)
    return box


def _new_out(name: str, ext: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    return str(outbox_dir() / f"{name}_{ts}_{uid}.{ext}")


class PdfCraftEngine:
    """Headless PdfCraft subprocess wrapper."""

    def __init__(self, cli: Path | None = None, timeout_s: int = 120) -> None:
        self.cli = cli or cli_path()
        self.timeout_s = int(os.getenv("PDFCRAFT_TIMEOUT_S", str(timeout_s)))

    def status(self) -> dict:
        """Report CLI presence, version, and outbox. Never raises."""
        if not is_enabled():
            return {"success": True, "enabled": False, "installed": False, "message": "PdfCraft bridge disabled via PDFCRAFT_ENABLED=0."}
        exe = str(self.cli)
        if not self.cli.exists():
            found = shutil.which("pdfcraft-cli.exe")
            if found:
                self.cli = Path(found)
            else:
                return {
                    "success": False,
                    "enabled": True,
                    "installed": False,
                    "error": f"PdfCraft CLI not found: {exe}",
                    "error_type": "wrappee_missing",
                    "hint": "Install PdfCraft (https://getartcraft.com/apps/pdfcraft) or set PDFCRAFT_CLI.",
                }
        try:
            r = subprocess.run([str(self.cli), "--version"], capture_output=True, text=True, timeout=15)
            version = (r.stdout or r.stderr or "").strip().splitlines()[0] if (r.stdout or r.stderr) else "unknown"
        except Exception as e:
            return {"success": False, "enabled": True, "installed": True, "error": str(e), "error_type": type(e).__name__}
        return {
            "success": True,
            "enabled": True,
            "installed": True,
            "cli": str(self.cli),
            "version": version,
            "outbox": str(outbox_dir()),
            "message": f"PdfCraft ready ({version}).",
        }

    def _run(self, args: list[str], timeout: int | None = None) -> dict:
        st = self.status()
        if not st.get("success"):
            return st
        try:
            r = subprocess.run([str(self.cli), *args], capture_output=True, text=True, timeout=timeout or self.timeout_s)
        except subprocess.TimeoutExpired:
            logger.warning("pdfcraft timeout: %s", args[:3])
            return {"success": False, "error": f"PdfCraft timed out after {timeout or self.timeout_s}s: {' '.join(args[:3])}", "error_type": "engine_timeout"}
        except Exception as e:
            logger.exception("pdfcraft spawn failed: %s", e)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}
        if r.returncode != 0:
            err = (r.stderr or r.stdout or f"exit {r.returncode}").strip()[-2000:]
            return {"success": False, "error": err, "error_type": "engine_error", "exit_code": r.returncode}
        return {"success": True, "stdout": r.stdout or "", "stderr": r.stderr or ""}

    def info(self, path: str) -> dict:
        r = self._run(["info", path])
        if not r.get("success"):
            return r
        try:
            data = json.loads(r["stdout"])
            return {"success": True, "info": data, "message": f"PdfCraft info: {data.get('pages', '?')} pages."}
        except Exception:
            return {"success": True, "info": {"raw": r["stdout"][:4000]}, "message": "PdfCraft info (unparsed)."}

    def text(self, path: str, page: int | None = None) -> dict:
        args = ["text", path] + (["--page", str(page)] if page else [])
        r = self._run(args)
        if not r.get("success"):
            return r
        return {"success": True, "text": r["stdout"], "message": f"Extracted {len(r['stdout'])} chars via PdfCraft."}

    def render(self, path: str, page: int = 1, dpi: int = 96, out_path: str | None = None) -> dict:
        out = out_path or _new_out(Path(path).stem + f"_p{page}", "png")
        r = self._run(["render", path, "--page", str(page), "--dpi", str(dpi), "--out", out])
        if not r.get("success"):
            return r
        return {"success": True, "path": out, "page": page, "dpi": dpi, "message": f"Rendered page {page} to {Path(out).name}."}

    def combine(self, paths: list[str], out_path: str | None = None) -> dict:
        if len(paths) < 2:
            return {"success": False, "error": "combine needs at least 2 PDFs.", "error_type": "InvalidInput"}
        out = out_path or _new_out(Path(paths[0]).stem + "_portfolio", "pdf")
        r = self._run(["combine", *paths, "--out", out])
        if not r.get("success"):
            return r
        return {"success": True, "path": out, "message": f"Combined {len(paths)} PDFs into {Path(out).name}."}

    def extract_pages(self, path: str, pages: str, out_path: str | None = None) -> dict:
        out = out_path or _new_out(Path(path).stem + "_extract", "pdf")
        r = self._run(["extract", path, "--pages", pages, "--out", out])
        if not r.get("success"):
            return r
        return {"success": True, "path": out, "pages": pages, "message": f"Extracted pages {pages} to {Path(out).name}."}

    def split_every(self, path: str, every: int, out_dir: str | None = None) -> dict:
        target = Path(out_dir) if out_dir else (outbox_dir() / f"{Path(path).stem}_split_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        target.mkdir(parents=True, exist_ok=True)
        r = self._run(["split", path, "--every", str(every), "--out-dir", str(target)], timeout=180)
        if not r.get("success"):
            return r
        files = sorted(str(p) for p in target.glob("*.pdf"))
        return {"success": True, "files": files, "out_dir": str(target), "message": f"Split into {len(files)} files."}

    def edit(self, path: str, out_path: str | None = None, rotate: str | None = None, delete: str | None = None, title: str | None = None, author: str | None = None) -> dict:
        out = out_path or _new_out(Path(path).stem + "_edit", "pdf")
        args = ["edit", path, "--out", out]
        if rotate:
            args += ["--rotate", rotate]
        if delete:
            args += ["--delete", delete]
        if title:
            args += ["--title", title]
        if author:
            args += ["--author", author]
        r = self._run(args)
        if not r.get("success"):
            return r
        return {"success": True, "path": out, "message": f"Edited {Path(path).name} -> {Path(out).name}."}

    def audit(self, path: str) -> dict:
        r = self._run(["audit", path])
        if r.get("success"):
            return {"success": True, "clean": True, "message": f"No faux redactions in {Path(path).name}."}
        if r.get("error_type") == "engine_error":
            return {"success": True, "clean": False, "detail": r.get("error", "")[:2000], "message": f"Faux redactions FOUND in {Path(path).name}."}
        return r

    def batch(self, paths: list[str], steps: list[str], out_dir: str | None = None, recursive: bool = False) -> dict:
        target = Path(out_dir) if out_dir else (outbox_dir() / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}")
        target.mkdir(parents=True, exist_ok=True)
        r = self._run(["batch", *paths, "--steps", ",".join(steps), "--out-dir", str(target)] + (["--recursive"] if recursive else []), timeout=600)
        if not r.get("success"):
            return r
        return {"success": True, "out_dir": str(target), "log": r["stdout"][-4000:], "message": f"Batch {','.join(steps)} done -> {target.name}."}
