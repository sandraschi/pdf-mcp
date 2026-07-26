import os
from pathlib import Path

import fitz
import pdfplumber


class Extractor:
    def extract_text(self, path: str, page_nums: list[int] | None = None) -> dict:
        try:
            doc = fitz.open(path)
            total_pages = len(doc)
            text_parts = []
            pages = page_nums if page_nums else range(total_pages)
            for i in pages:
                if i < 0 or i >= total_pages:
                    continue
                text_parts.append(doc[i].get_text())
            doc.close()
            return {"success": True, "text": "\n".join(text_parts), "pages": len(pages), "page_count": total_pages}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_images(self, path: str, output_dir: str, page_nums: list[int] | None = None) -> dict:
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            doc = fitz.open(path)
            total_pages = len(doc)
            pages = page_nums if page_nums else range(total_pages)
            images = []
            for i in pages:
                if i < 0 or i >= total_pages:
                    continue
                page = doc[i]
                for idx, img in enumerate(page.get_images(full=True)):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    ext = base_image["ext"]
                    w = base_image["width"]
                    h = base_image["height"]
                    img_path = str(Path(output_dir) / f"page_{i + 1}_img_{idx}.{ext}")
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)
                    images.append({"page": i + 1, "index": idx, "width": w, "height": h, "path": img_path, "ext": ext})
            doc.close()
            return {"success": True, "images": images}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_tables(self, path: str, page_nums: list[int] | None = None) -> dict:
        try:
            pdf = pdfplumber.open(path)
            total_pages = len(pdf.pages)
            pages = page_nums if page_nums else range(total_pages)
            tables = []
            for i in pages:
                if i < 0 or i >= total_pages:
                    continue
                page = pdf.pages[i]
                page_tables = page.extract_tables()
                for t in page_tables:
                    if not t:
                        continue
                    headers = t[0] if t else []
                    data = t[1:] if len(t) > 1 else []
                    rows = len(data)
                    cols = len(headers) if headers else (len(data[0]) if data else 0)
                    tables.append(
                        {
                            "page": i + 1,
                            "rows": rows,
                            "cols": cols,
                            "headers": headers,
                            "data": data,
                        }
                    )
            pdf.close()
            return {"success": True, "tables": tables}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_metadata(self, path: str) -> dict:
        try:
            doc = fitz.open(path)
            meta = doc.metadata or {}
            fsize = os.path.getsize(path)
            result = {
                "title": meta.get("title", ""),
                "author": meta.get("author", ""),
                "subject": meta.get("subject", ""),
                "keywords": meta.get("keywords", ""),
                "creator": meta.get("creator", ""),
                "producer": meta.get("producer", ""),
                "creation_date": meta.get("creationDate", ""),
                "mod_date": meta.get("modDate", ""),
                "page_count": len(doc),
                "file_size": fsize,
            }
            doc.close()
            return {"success": True, "metadata": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_fonts(self, path: str) -> dict:
        try:
            doc = fitz.open(path)
            fonts = []
            seen = set()
            for i in range(len(doc)):
                page_fonts = doc[i].get_fonts()
                for f in page_fonts:
                    key = (f[0], f[1], f[3])
                    if key not in seen:
                        seen.add(key)
                        fonts.append(
                            {
                                "name": f[0],
                                "type": f[1],
                                "encoding": f[2],
                                "embedded": f[4],
                                "size": f[3],
                            }
                        )
            doc.close()
            return {"success": True, "fonts": fonts}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_links(self, path: str) -> dict:
        try:
            doc = fitz.open(path)
            links = []
            for i in range(len(doc)):
                page_links = doc[i].get_links()
                for link in page_links:
                    uri = link.get("uri")
                    page_target = link.get("page")
                    link_type = link.get("kind", 0)
                    rect = link.get("from")
                    links.append(
                        {
                            "page": i + 1,
                            "rect": {"x0": rect.x0, "y0": rect.y0, "x1": rect.x1, "y1": rect.y1} if rect else None,
                            "uri": uri,
                            "page_target": page_target,
                            "type": link_type,
                        }
                    )
            doc.close()
            return {"success": True, "links": links}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_outline(self, path: str) -> dict:
        try:
            doc = fitz.open(path)
            toc = doc.get_toc()
            outline = self._build_outline_tree(toc)
            doc.close()
            return {"success": True, "outline": outline}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_outline_tree(self, toc: list) -> list:
        root = []
        stack = [root]
        prev_level = 0
        for entry in toc:
            level, title, page = entry[0], entry[1], entry[2]
            node = {"title": title, "level": level, "page": page, "children": []}
            if level > prev_level:
                for _ in range(level - prev_level - 1):
                    if len(stack) <= prev_level:
                        break
                if len(stack) > prev_level:
                    stack[prev_level].append(node)
                else:
                    stack[-1].append(node)
            elif level == prev_level:
                stack[-1].append(node)
            else:
                for _ in range(prev_level - level):
                    stack.pop()
                stack[-1].append(node)
            stack.append(node["children"])
            prev_level = level
        return root
