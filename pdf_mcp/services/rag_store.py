from pathlib import Path

import lancedb


class RagStore:
    def __init__(self, db_path: str | Path):
        self._db = lancedb.connect(str(db_path))
        self._table_name = "pdf_chunks"
        self._doc_counts: dict[str, int] = {}
        self._ensure_table()

    def _ensure_table(self):
        try:
            self._table = self._db.open_table(self._table_name)
        except Exception:
            self._table = self._db.create_table(
                self._table_name,
                data=[
                    {
                        "vector": [0.0] * self.get_embedding_dim(),
                        "doc_id": "",
                        "chunk_id": "",
                        "page_num": 0,
                        "text": "",
                        "section": "",
                        "metadata": {},
                    }
                ],
            )
            self._table.delete("doc_id = ''")

    def index_chunks(self, chunks: list[dict], embeddings: list[list[float]]) -> dict:
        try:
            if not chunks or not embeddings:
                return {"success": True, "count": 0}
            data = []
            for chunk, vec in zip(chunks, embeddings):
                data.append(
                    {
                        "vector": vec,
                        "doc_id": chunk.get("doc_id", "unknown"),
                        "chunk_id": chunk.get("chunk_id", ""),
                        "page_num": chunk.get("page_num", 0),
                        "text": chunk.get("text", ""),
                        "section": chunk.get("section") or "",
                        "metadata": chunk.get("metadata", {}),
                    }
                )
            self._table.add(data)
            for chunk, vec in zip(chunks, embeddings):
                doc_id = chunk.get("doc_id", "unknown")
                self._doc_counts[doc_id] = self._doc_counts.get(doc_id, 0) + 1
            return {"success": True, "count": len(data)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search(self, query_embedding: list[float], limit: int = 10) -> dict:
        try:
            results = self._table.search(query_embedding).limit(limit).to_list()
            clean = []
            for r in results:
                clean.append(
                    {
                        "doc_id": r.get("doc_id", ""),
                        "chunk_id": r.get("chunk_id", ""),
                        "page_num": r.get("page_num", 0),
                        "text": r.get("text", ""),
                        "section": r.get("section"),
                        "metadata": r.get("metadata", {}),
                        "_distance": r.get("_distance"),
                    }
                )
            return {"success": True, "results": clean}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_documents(self) -> dict:
        try:
            docs = [{"doc_id": doc_id, "chunk_count": count} for doc_id, count in sorted(self._doc_counts.items())]
            return {"success": True, "documents": docs}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_document(self, doc_id: str) -> dict:
        try:
            self._table.delete(f"doc_id = '{doc_id}'")
            self._doc_counts.pop(doc_id, None)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_all(self) -> dict:
        try:
            self._db.drop_table(self._table_name)
            self._ensure_table()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_embedding_dim(self) -> int:
        return 384
