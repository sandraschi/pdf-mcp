import os
from pathlib import Path

import fitz
from pypdf import PdfReader, PdfWriter


class Manipulator:
    def merge(self, pdf_paths: list[str], output_path: str) -> dict:
        try:
            writer = PdfWriter()
            for p in pdf_paths:
                reader = PdfReader(p)
                for page in reader.pages:
                    writer.add_page(page)
            with open(output_path, "wb") as f:
                writer.write(f)
            return {"success": True, "path": output_path, "pages": len(writer.pages)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def split(self, pdf_path: str, output_dir: str, ranges: list[list[int]] | None = None) -> dict:
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            reader = PdfReader(pdf_path)
            base = Path(pdf_path).stem
            files = []
            if ranges:
                for r in ranges:
                    start = max(r[0] - 1, 0)
                    end = min(r[1], len(reader.pages))
                    writer = PdfWriter()
                    for i in range(start, end):
                        writer.add_page(reader.pages[i])
                    out = str(Path(output_dir) / f"{base}_p{r[0]}-{r[1]}.pdf")
                    with open(out, "wb") as f:
                        writer.write(f)
                    files.append(out)
            else:
                for i in range(len(reader.pages)):
                    writer = PdfWriter()
                    writer.add_page(reader.pages[i])
                    out = str(Path(output_dir) / f"{base}_p{i + 1}.pdf")
                    with open(out, "wb") as f:
                        writer.write(f)
                    files.append(out)
            return {"success": True, "files": files}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def rotate(self, pdf_path: str, output_path: str, pages: list[int] | None = None, angle: int = 90) -> dict:
        try:
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            for i in range(len(reader.pages)):
                page = reader.pages[i]
                if pages is None or (i + 1) in pages:
                    page.rotate(angle)
                writer.add_page(page)
            with open(output_path, "wb") as f:
                writer.write(f)
            return {"success": True, "path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def reorder(self, pdf_path: str, output_path: str, new_order: list[int]) -> dict:
        try:
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            total = len(reader.pages)
            for idx in new_order:
                if 1 <= idx <= total:
                    writer.add_page(reader.pages[idx - 1])
            with open(output_path, "wb") as f:
                writer.write(f)
            return {"success": True, "path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_pages(self, pdf_path: str, output_path: str, pages: list[int]) -> dict:
        try:
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            delete_set = set(pages)
            for i in range(len(reader.pages)):
                if (i + 1) not in delete_set:
                    writer.add_page(reader.pages[i])
            with open(output_path, "wb") as f:
                writer.write(f)
            return {"success": True, "path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def compress(self, pdf_path: str, output_path: str, quality: int = 85) -> dict:
        try:
            orig_size = os.path.getsize(pdf_path)
            doc = fitz.open(pdf_path)
            for i in range(len(doc)):
                for img in doc[i].get_images(full=True):
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n > 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    if quality < 100:
                        fitz.Pixmap(fitz.csRGB, pix)
                    doc.replace_image(xref, pixmap=pix)
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()
            new_size = os.path.getsize(output_path)
            return {"success": True, "path": output_path, "original_size": orig_size, "compressed_size": new_size}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def encrypt(self, pdf_path: str, output_path: str, password: str) -> dict:
        try:
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(password)
            with open(output_path, "wb") as f:
                writer.write(f)
            return {"success": True, "path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def decrypt(self, pdf_path: str, output_path: str, password: str) -> dict:
        try:
            reader = PdfReader(pdf_path)
            if reader.is_encrypted:
                reader.decrypt(password)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            with open(output_path, "wb") as f:
                writer.write(f)
            return {"success": True, "path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def optimize(self, pdf_path: str, output_path: str) -> dict:
        try:
            orig_size = os.path.getsize(pdf_path)
            doc = fitz.open(pdf_path)
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()
            new_size = os.path.getsize(output_path)
            return {"success": True, "path": output_path, "original_size": orig_size, "optimized_size": new_size}
        except Exception as e:
            return {"success": False, "error": str(e)}
