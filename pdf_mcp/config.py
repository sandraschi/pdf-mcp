import os
from pathlib import Path


class Config:
    host: str = os.getenv("MCP_HOST", "127.0.0.1")
    port: int = int(os.getenv("MCP_PORT", "11131"))
    frontend_port: int = int(os.getenv("FRONTEND_PORT", "11130"))
    mode: str = os.getenv("MCP_MODE", "stdio")

    # Paths
    repo_root: Path = Path(__file__).resolve().parent.parent
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", str(repo_root / "data" / "uploads")))
    rag_store_path: Path = Path(os.getenv("RAG_STORE_PATH", str(repo_root / "data" / "lancedb")))

    # RAG
    rag_embedding_url: str | None = os.getenv("RAG_EMBEDDING_URL") or None
    rag_embedding_model: str = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # Tauri
    is_tauri: bool = os.getenv("PDF_MCP_TAURI", "").lower() in ("1", "true", "yes")

    # Server identity
    server_name: str = "pdf-mcp"
    version: str = "0.1.0"
    server_description: str = "Full-stack PDF intelligence — extract, manipulate, annotate, convert, validate, RAG-search"

    def ensure_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.rag_store_path.mkdir(parents=True, exist_ok=True)


cfg = Config()
