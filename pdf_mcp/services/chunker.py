import re


class Chunker:
    def chunk_by_page(self, pages: list[dict], max_chars: int = 2000) -> list[dict]:
        try:
            chunks = []
            for pg in pages:
                text = pg.get("text", "")
                page_num = pg.get("page_num", 0)
                section = pg.get("section")
                doc_id = pg.get("doc_id", "unknown")
                metadata = pg.get("metadata", {})
                if len(text) <= max_chars:
                    chunks.append(
                        {
                            "doc_id": doc_id,
                            "chunk_id": f"{doc_id}_p{page_num}",
                            "page_num": page_num,
                            "text": text,
                            "section": section,
                            "metadata": metadata,
                        }
                    )
                else:
                    start = 0
                    part = 0
                    while start < len(text):
                        end = min(start + max_chars, len(text))
                        chunk_text = text[start:end]
                        chunks.append(
                            {
                                "doc_id": doc_id,
                                "chunk_id": f"{doc_id}_p{page_num}_{part}",
                                "page_num": page_num,
                                "text": chunk_text,
                                "section": section,
                                "metadata": {**metadata, "chunk_part": part},
                            }
                        )
                        start = end
                        part += 1
            return chunks
        except Exception:
            return []

    def chunk_by_section(self, text: str, metadata: dict, min_chars: int = 500, max_chars: int = 2000) -> list[dict]:
        try:
            sections = re.split(r"(^|\n)(#{1,6}\s+.*)", text, flags=re.MULTILINE)
            chunks = []
            doc_id = metadata.get("doc_id", "unknown")
            buffer = ""
            current_section = None
            idx = 0
            for part in sections:
                if not part:
                    continue
                if re.match(r"^#{1,6}\s+", part.strip()):
                    if buffer:
                        chunk_text = buffer.strip()
                        if chunk_text:
                            chunks.append(
                                {
                                    "doc_id": doc_id,
                                    "chunk_id": f"{doc_id}_s{idx}",
                                    "page_num": metadata.get("page_num", 0),
                                    "text": chunk_text,
                                    "section": current_section,
                                    "metadata": metadata,
                                }
                            )
                            idx += 1
                    current_section = part.strip().lstrip("# ")
                    buffer = part + "\n"
                else:
                    buffer += part + "\n"
                    if len(buffer) >= max_chars:
                        chunks.append(
                            {
                                "doc_id": doc_id,
                                "chunk_id": f"{doc_id}_s{idx}",
                                "page_num": metadata.get("page_num", 0),
                                "text": buffer.strip(),
                                "section": current_section,
                                "metadata": metadata,
                            }
                        )
                        buffer = ""
                        idx += 1
            if buffer.strip():
                if len(buffer.strip()) >= min_chars or not chunks:
                    chunks.append(
                        {
                            "doc_id": doc_id,
                            "chunk_id": f"{doc_id}_s{idx}",
                            "page_num": metadata.get("page_num", 0),
                            "text": buffer.strip(),
                            "section": current_section,
                            "metadata": metadata,
                        }
                    )
            return chunks
        except Exception:
            return []

    def chunk_recursive(self, text: str, metadata: dict, chunk_size: int = 1000, overlap: int = 200) -> list[dict]:
        try:
            doc_id = metadata.get("doc_id", "unknown")
            separators = ["\n\n", "\n", " ", ""]
            chunks = []
            self._recursive_split(text, metadata, doc_id, separators, 0, chunk_size, overlap, chunks)
            return chunks
        except Exception:
            return []

    def _recursive_split(
        self,
        text: str,
        metadata: dict,
        doc_id: str,
        separators: list,
        sep_idx: int,
        chunk_size: int,
        overlap: int,
        output: list,
    ):
        if not text:
            return
        sep = separators[sep_idx] if sep_idx < len(separators) else ""
        if sep:
            parts = text.split(sep)
        else:
            parts = list(text)

        if len(parts) == 1 or sep_idx >= len(separators) - 1:
            for i in range(0, len(text), chunk_size - overlap):
                chunk_text = text[i : i + chunk_size]
                if not chunk_text:
                    continue
                output.append(
                    {
                        "doc_id": doc_id,
                        "chunk_id": f"{doc_id}_r{len(output)}",
                        "page_num": metadata.get("page_num", 0),
                        "text": chunk_text,
                        "section": metadata.get("section"),
                        "metadata": {**metadata, "chunk_index": len(output)},
                    }
                )
            return

        current = ""
        for part in parts:
            if not part:
                continue
            if len(current) + len(part) + len(sep) <= chunk_size:
                current += (sep if current else "") + part
            else:
                if current:
                    output.append(
                        {
                            "doc_id": doc_id,
                            "chunk_id": f"{doc_id}_r{len(output)}",
                            "page_num": metadata.get("page_num", 0),
                            "text": current,
                            "section": metadata.get("section"),
                            "metadata": {**metadata, "chunk_index": len(output)},
                        }
                    )
                overlap_text = current[-overlap:] if len(current) > overlap else current
                current = overlap_text + (sep if overlap_text else "") + part
                if len(current) > chunk_size:
                    self._recursive_split(current, metadata, doc_id, separators, sep_idx + 1, chunk_size, overlap, output)
                    current = ""

        if current:
            output.append(
                {
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_r{len(output)}",
                    "page_num": metadata.get("page_num", 0),
                    "text": current,
                    "section": metadata.get("section"),
                    "metadata": {**metadata, "chunk_index": len(output)},
                }
            )

    def chunk_semantic(self, text: str, metadata: dict) -> list[dict]:
        try:
            doc_id = metadata.get("doc_id", "unknown")
            paragraphs = re.split(r"\n\s*\n", text)
            chunks = []
            chunk_max = 2000
            current = ""
            idx = 0
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                if len(current) + len(para) + 2 <= chunk_max:
                    current += "\n\n" + para if current else para
                else:
                    if current:
                        chunks.append(
                            {
                                "doc_id": doc_id,
                                "chunk_id": f"{doc_id}_sem{idx}",
                                "page_num": metadata.get("page_num", 0),
                                "text": current,
                                "section": metadata.get("section"),
                                "metadata": {**metadata, "chunk_index": idx},
                            }
                        )
                        idx += 1
                    if len(para) > chunk_max:
                        for i in range(0, len(para), chunk_max):
                            chunks.append(
                                {
                                    "doc_id": doc_id,
                                    "chunk_id": f"{doc_id}_sem{idx}",
                                    "page_num": metadata.get("page_num", 0),
                                    "text": para[i : i + chunk_max],
                                    "section": metadata.get("section"),
                                    "metadata": {**metadata, "chunk_index": idx},
                                }
                            )
                            idx += 1
                    else:
                        current = para
            if current:
                chunks.append(
                    {
                        "doc_id": doc_id,
                        "chunk_id": f"{doc_id}_sem{idx}",
                        "page_num": metadata.get("page_num", 0),
                        "text": current,
                        "section": metadata.get("section"),
                        "metadata": {**metadata, "chunk_index": idx},
                    }
                )
            return chunks
        except Exception:
            return []
