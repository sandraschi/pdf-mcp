# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — produce pdf-mcp-backend.exe for Tauri NSIS embedding.
# Fleet standard: strip=False, upx=False, noarchive=True (see tauri_nsis_building.md).
# Usage (from repo root):
#   uv run pyinstaller pdf-mcp-backend.spec --distpath dist --clean --noconfirm

block_cipher = None

a = Analysis(
    ["pdf_mcp/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[("pdf_mcp", "pdf_mcp")],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "h11",
        "beartype",
        "websockets",
        "sqlite3",
        "_strptime",
        "_datetime",
        "cachetools",
        "pytz",
        "jsonschema",
        "joserfc",
        "joserfc.jwk",
        "joserfc.jwt",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "setuptools", "pip", "wheel", "test", "tests", "unittest", "_distutils_hack"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=True,
)
# Strip .dist-info but preserve metadata for packages that need it at runtime
_keep_dist = ["fastmcp-", "fastmcp_slim-", "mcp-", "prefab_ui-", "opentelemetry-", "email_validator-", "lancedb-", "pyarrow-"]
_saved = [
    e
    for e in a.datas
    if isinstance(e, tuple) and any(k in str(e[0]) for k in _keep_dist) and ".dist-info" in str(e[0])
]
for _list in [a.datas, a.binaries, a.zipfiles, a.scripts]:
    _list[:] = [e for e in _list if not (isinstance(e, tuple) and ".dist-info" in str(e[0]))]
a.datas.extend(_saved)
SKIP = [
    "torch",
    "playwright",
    "bitsandbytes",
    "llvmlite",
    "grpc",
    "numba",
    "Cython",
    "google",
    "azure",
    "boto3",
    "botocore",
    "matplotlib",
    "pandas",
    "scipy",
    "sklearn",
    "onnxruntime",
]
# Path-segment match, not raw substring: a raw "s in path" check false-positived on
# numpy's bundled OpenBLAS DLL (numpy.libs/libscipy_openblas64_-<hash>.dll), which
# contains the substring "scipy" in its filename despite belonging to numpy, not
# scipy. Require the skip name to be a whole path token (dir or file-stem boundary).
import re as _re


def _is_skipped_binary(path: str) -> bool:
    tokens = _re.split(r"[\\/]", path.lower())
    for skip in SKIP:
        for tok in tokens:
            if tok == skip or tok.startswith(skip + ".") or tok.startswith(skip + "-") or tok.startswith(skip + "_"):
                return True
    return False


a.binaries = [b for b in a.binaries if not _is_skipped_binary(b[0])]
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="pdf-mcp-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
)
