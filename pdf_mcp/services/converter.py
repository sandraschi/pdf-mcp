from pathlib import Path
from typing import Any, cast

import fitz
from PIL import Image


class Converter:
    def to_markdown(self, pdf_path: str, output_path: str | None = None) -> dict:
        try:
            doc = fitz.open(pdf_path)
            lines = []
            for i in range(len(doc)):
                page = doc[i]
                blocks = cast(dict[str, Any], page.get_text("dict"))["blocks"]
                for b in blocks:
                    if b.get("type") != 0:
                        continue
                    for line in b.get("lines", []):
                        spans = line.get("spans", [])
                        if not spans:
                            continue
                        text = spans[0]["text"]
                        size = spans[0]["size"]
                        is_bold = any(s.get("flags", 0) & 2 for s in spans)
                        is_heading = size > 14 or (size > 12 and is_bold)
                        if is_heading:
                            text = f"## {text}" if size > 14 else f"### {text}"
                        lines.append(text)
                    lines.append("")
            markdown = "\n".join(lines).strip()
            page_count = len(doc)
            path = None
            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(markdown)
                path = output_path
            doc.close()
            return {"success": True, "markdown": markdown, "path": path, "pages": page_count}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def to_images(self, pdf_path: str, output_dir: str, fmt: str = "png", dpi: int = 200) -> dict:
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            doc = fitz.open(pdf_path)
            images = []
            for i in range(len(doc)):
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = doc[i].get_pixmap(matrix=mat)
                img_path = str(Path(output_dir) / f"page_{i + 1}.{fmt}")
                pix.save(img_path)
                images.append({"page": i + 1, "path": img_path, "width": pix.width, "height": pix.height})
            doc.close()
            return {"success": True, "images": images}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def to_html(self, pdf_path: str, output_path: str | None = None) -> dict:
        try:
            doc = fitz.open(pdf_path)
            parts = [f"<html><body><h1>{Path(pdf_path).stem}</h1>"]
            for i in range(len(doc)):
                text = str(doc[i].get_text())
                parts.append(f"<div class='page' id='page-{i + 1}'><h2>Page {i + 1}</h2><p>{text.replace(chr(10), '<br>')}</p></div>")
            parts.append("</body></html>")
            html = "\n".join(parts)
            path = None
            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html)
                path = output_path
            doc.close()
            return {"success": True, "html": html, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def from_html(self, html_content: str, output_path: str) -> dict:
        try:
            import re

            texts = re.findall(r">([^<]+)<", html_content)
            doc = fitz.open()
            page = doc.new_page()
            y = 50
            for t in texts:
                t = t.strip()
                if not t:
                    continue
                if y > 780:
                    page = doc.new_page()
                    y = 50
                page.insert_text(fitz.Point(50, y), t, fontsize=11)
                y += 18
            page_count = len(doc)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()
            return {"success": True, "path": output_path, "pages": page_count}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def from_markdown(self, md_content: str, output_path: str) -> dict:
        try:
            doc = fitz.open()
            page = doc.new_page()
            y = 50
            for line in md_content.split("\n"):
                line = line.rstrip()
                if not line:
                    y += 10
                    continue
                if y > 780:
                    page = doc.new_page()
                    y = 50
                is_heading = line.startswith("##")
                fs = 16 if line.startswith("# ") else (14 if line.startswith("## ") else (12 if is_heading else 10))
                display = line.lstrip("# ")
                page.insert_text(fitz.Point(50, y), display, fontsize=fs)
                y += fs * 1.5 if is_heading else 16
            page_count = len(doc)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()
            return {"success": True, "path": output_path, "pages": page_count}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def from_images(self, image_paths: list[str], output_path: str) -> dict:
        try:
            doc = fitz.open()
            for img_path in image_paths:
                pil_img = Image.open(img_path)
                w, h = pil_img.size
                rect = fitz.Rect(0, 0, w, h)
                page = doc.new_page(width=w, height=h)
                page.insert_image(rect, filename=img_path)
            page_count = len(doc)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()
            return {"success": True, "path": output_path, "pages": page_count}
        except Exception as e:
            return {"success": False, "error": str(e)}
