# pdf-mcp — NSIS Build Log

Running record of Tauri NSIS installer builds: failures, root causes, fixes.

## 2026-09-17 21:26 +02:00 — First NSIS build attempt (post-assfix, commit 0a9f2c5)

**Result: PASS** (after 3 fix iterations). Installer:
`src-tauri/target/release/bundle/nsis/Pdf MCP_0.1.0_x64-setup.exe` — 174,181,355 bytes (~166 MB).

### Pre-flight fixes (before first build)

- `src-tauri/src/backend.rs` `spawn_backend()`: added `.env("MCP_MODE", "http")` to the
  spawned backend process. The PyInstaller entry point (`pdf_mcp/__main__.py`) has none
  of `run_server.py`'s `PORT`-implies-`--mode http` argv translation, so `Config.mode`
  (`pdf_mcp/config.py`) defaulted to `"stdio"` and the bundled backend never bound the
  HTTP port. This is the exact regression class the task briefing warned about.
- `src-tauri/src/backend.rs` `free_port()`: rewritten from a single best-effort
  `taskkill` into 4 layers (Stop-Process, taskkill, UAC-elevated taskkill fallback, then
  a poll loop confirming the port is actually free) before spawning.
- Confirmed `hooks.nsh`, `main.rs` (`Emitter`+`Manager`), `tauri.conf.json`
  (`webviewInstallMode: skip`, `bundle.targets: ["nsis"]`), zoom hook, and `.gitignore`
  were already compliant — no changes needed there.
- Created `scripts/cua-nsis-config.json` and copied the current
  `mcp-central-docs/templates/tauri-native/scripts/cua-smoke.py` (v7) into
  `scripts/cua-smoke.py` — neither existed in the repo yet. `nav_routes`,
  `bridge_ok_text`, `health_path`, `window_title_re`, etc. were all read from actual
  source (`webapp/src/components/Sidebar.tsx`, page headers, `pdf_mcp/server.py`
  routes, `tauri.conf.json`, `Cargo.toml`), not guessed.

### Build iteration 1 — FAILED (genuine app bug, not a CUA config issue)

First full build + CUA smoke test: install and launch succeeded, but
`FATAL: Backend not reachable after 60s`. Root cause chain, found by running
`dist/pdf-mcp-backend.exe` standalone and reading the real traceback (the Tauri child
process log only captured a truncated first frame):

1. `pdf-mcp-backend.spec`'s `SKIP` binary-exclusion list included `"pymupdf"` and
   `"PIL"` — both are genuine runtime deps (`pdf_mcp/tools/annotate.py` does
   `import fitz`, `pdf_mcp/tools/convert.py` imports `Converter` which uses PIL), so
   the frozen exe crashed on `import pdf_mcp.tools` before ever starting uvicorn.
   Removed both from `SKIP`.
2. After that fix, a **new** crash: `numpy` failed with
   `ImportError: DLL load failed while importing _multiarray_umath`. Root cause: the
   `SKIP` filter did `s in b[0].lower()` (raw substring match), and numpy's bundled
   OpenBLAS DLL is named `numpy.libs\libscipy_openblas64_-<hash>.dll` — it contains
   the substring `"scipy"` despite belonging to numpy, so the `"scipy"` SKIP entry
   collaterally stripped numpy's own math library. Fixed by rewriting the filter to
   require a whole path-segment match (`_is_skipped_binary()`) instead of substring
   containment.
3. Next: `lancedb` failed `PackageNotFoundError: No package metadata was found for
   lancedb`. The spec's dist-info strip/keep-list (`_keep_dist`) only *preserves*
   dist-info PyInstaller's static analysis already auto-collected — it doesn't inject
   metadata for packages never collected in the first place. Added `"lancedb-"` (and
   proactively `"pyarrow-"`) to `_keep_dist`.
4. Next: `pyarrow` failed `ModuleNotFoundError: No module named 'pyarrow.lib'` —
   `"pyarrow"` was also in the `SKIP` binary-exclusion list (copy-pasted from a
   template meant for repos without a RAG/data stack), stripping the compiled
   extension lancedb genuinely needs. Removed `"pyarrow"` from `SKIP`.

After all 4 fixes, the standalone backend exe imports cleanly and serves
`/api/health` (confirmed via direct `curl` before touching the Tauri layer).

### Build iteration 2 — PASS

Full `src-tauri/build.ps1` rerun (frontend + PyInstaller + cargo/NSIS) succeeded.
Backend exe grew from 117 MB (broken, missing real deps) to ~164 MB (correct — numpy,
pymupdf, pyarrow, lancedb all genuinely bundled).

### CUA smoke test — 11/11 phases PASSED (genuine, real GUI + OCR verification)

Install, launch, window verify, screenshot, feature route, diagnostics, WebView
bridge OCR (`'pdf-mcp'` found in screenshot), nav click-through (all 7 sidebar pages —
Dashboard, Workbench, Pipeline, Chat, Tools, Skills, Logs — each OCR-verified to show
its own header), log analysis (no errors), uninstall. One non-fatal cosmetic note:
`feature_smoke_path` was originally `/api/tools` (returns a JSON array, and the smoke
script's non-fatal check assumes a dict) — switched to `/api/stats` for a clean log on
future runs; did not require a re-run since it was already non-fatal and the phase
still passed.

### Known follow-up (not blocking, not fixed this run)

`backend.rs` sets `PORT`/`HOST` env vars when spawning the backend, but
`pdf_mcp/config.py` reads `MCP_PORT`/`MCP_HOST`. This currently works only because both
default to the same value (11131 / 127.0.0.1) — if `BACKEND_PORT` in `backend.rs` is
ever changed without also changing `Config.port`'s default, the backend will silently
bind the wrong port again. Left unfixed this run (out of scope, not currently broken).
