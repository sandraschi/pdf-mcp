"""Document intelligence services: analysis, redaction, classification, dedupe, briefs."""

import difflib
import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Any, cast

import fitz

PII_PATTERNS: dict[str, str] = {
    "email": r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
    "us_phone": r"(?<!\d)(?:\(\d{3}\)|\d{3})[\s.\-]?\d{3}[\s.\-]?\d{4}(?!\d)",
    "at_phone": r"(?<!\d)\+?43[\s\-]?\d{1,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}(?!\d)",
    "iban": r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
    "credit_card": r"\b(?:\d{4}[ -]?){3}\d{4}\b",
    "ssn": r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b",
    "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
}

DOC_TYPE_SIGNALS: dict[str, list[str]] = {
    "invoice": ["invoice", "rechnung", "facture", "bill to", "total due", "amount due", "vat", "ust."],
    "receipt": ["receipt", "quittung", "bon", "amount paid", "payment received", "danke für ihren einkauf"],
    "report": ["report", "annual", "quarterly", "executive summary", "bericht"],
    "contract": ["agreement", "contract", "vertrag", "terms and conditions", "parties", "hereby agree"],
    "form": ["form", "application", "registration", "antrag", "please fill"],
    "resume": ["curriculum vitae", "cv", "lebenslauf", "resume", "experience", "references"],
    "presentation": ["slide", "agenda", "deck", "presentation", "präsentation"],
    "letter": ["dear ", "sincerely", "sehr geehrte", "mit freundlichen grüßen"],
    "scanned-document": ["scanned", "ocr", "scandate"],
}

FIELD_PATTERNS: dict[str, str] = {
    "invoice_number": r"(?i)\b(?:invoice|rechnung|inv\.?)\s*(?:no\.?|#|nr\.?)?\s*[:#]?\s*([A-Z0-9\-/]{4,})",
    "total": r"(?i)\b(?:total|summe|amount due|gesamt)[^\d]{0,12}([\d.,]{4,})\b",
    "date": r"\b(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}|\d{4}-\d{2}-\d{2})\b",
    "vendor": r"(?i)\b(?:vendor|supplier|lieferant|from|von)\s*[:#]?\s*([A-Za-z][A-Za-z0-9&.\- ]{3,40})",
}


class Analyzer:
    """Scanned-vs-digital detection and layout stats."""

    @staticmethod
    def analyze(path: str) -> dict:
        try:
            doc = fitz.open(path)
            try:
                total_chars = 0
                total_images = 0
                pages = len(doc)
                per_page = []
                for i in range(pages):
                    text = str(doc[i].get_text())
                    chars = len(text.strip())
                    images = len(doc[i].get_images(full=True))
                    total_chars += chars
                    total_images += images
                    per_page.append({"page": i + 1, "chars": chars, "images": images})
                chars_per_page = round(total_chars / pages, 1) if pages else 0.0
                has_text_layer = total_chars >= 10
                scanned = not has_text_layer and total_images > 0
                layout_hint = "digital" if has_text_layer else ("scanned" if scanned else "empty")
                return {
                    "success": True,
                    "pages": pages,
                    "has_text_layer": has_text_layer,
                    "scanned": scanned,
                    "chars_per_page": chars_per_page,
                    "total_chars": total_chars,
                    "image_count": total_images,
                    "layout_hint": layout_hint,
                    "per_page": per_page,
                }
            finally:
                doc.close()
        except Exception as e:
            return {"success": False, "error": str(e)}


class Redactor:
    """Blacken sensitive content by terms and/or PII patterns."""

    @staticmethod
    def _page_words(page) -> list[list]:
        return page.get_text("words")

    @staticmethod
    def redact(path: str, output_path: str, terms: list[str] | None = None, pii: bool = False, fill: tuple = (0, 0, 0)) -> dict:
        try:
            terms = [t for t in (terms or []) if t.strip()]
            doc = fitz.open(path)
            try:
                occurrences = 0
                for i in range(len(doc)):
                    page = doc[i]
                    text = str(page.get_text())
                    targets: list[str] = []
                    if terms:
                        targets.extend(terms)
                    if pii:
                        for label, pattern in PII_PATTERNS.items():
                            targets.extend(m.group(0) for m in re.finditer(pattern, text))
                    for target in targets:
                        for rect in page.search_for(target):
                            page.add_redact_annot(rect, fill=fill)
                            occurrences += 1
                    page.apply_redactions()
                doc.save(output_path, garbage=4, deflate=True)
                return {"success": True, "path": output_path, "occurrences": occurrences}
            finally:
                doc.close()
        except Exception as e:
            return {"success": False, "error": str(e)}


class Classifier:
    """Document-type classification with optional field extraction."""

    @staticmethod
    def classify(path: str) -> dict:
        try:
            doc = fitz.open(path)
            try:
                meta = doc.metadata or {}
                text = ""
                for i in range(min(len(doc), 3)):
                    text += str(doc[i].get_text()) + "\n"
                normalized = " ".join(text.split()).lower()
                if not normalized:
                    return {"success": True, "doc_type": "scanned-document", "confidence": 0.6, "fields": {}, "reasons": ["no text layer - possibly scanned"]}
                scores: dict[str, int] = {}
                for doc_type, signals in DOC_TYPE_SIGNALS.items():
                    score = sum(1 for s in signals if s in normalized)
                    if score:
                        scores[doc_type] = score
                if not scores:
                    return {"success": True, "doc_type": "other", "confidence": 0.3, "fields": {}, "reasons": ["no strong signals"]}
                best_type, best_score = max(scores.items(), key=lambda kv: kv[1])
                fields: dict[str, str] = {}
                for label, pattern in FIELD_PATTERNS.items():
                    m = re.search(pattern, text)
                    if m and m.group(1):
                        fields[label] = m.group(1).strip()
                reasons = [f"{t}(x{c})" for t, c in sorted(scores.items(), key=lambda kv: -kv[1])[:3]]
                confidence = round(min(0.95, 0.45 + 0.15 * best_score), 2)
                return {
                    "success": True,
                    "doc_type": best_type,
                    "confidence": confidence,
                    "fields": fields,
                    "reasons": reasons,
                    "title": meta.get("title", "") or None,
                }
            finally:
                doc.close()
        except Exception as e:
            return {"success": False, "error": str(e)}


class Deduper:
    """Fingerprint and near-duplicate detection."""

    @staticmethod
    def _fingerprint(text: str) -> str:
        normalized = re.sub(r"\s+", " ", text).strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def dedupe(paths: list[str], threshold: float = 0.85) -> dict:
        try:
            docs: list[dict[str, Any]] = []
            for p in paths:
                doc = fitz.open(p)
                try:
                    text = " ".join(str(doc[i].get_text()) for i in range(len(doc)))
                finally:
                    doc.close()
                docs.append({"path": p, "name": Path(p).name, "text": text, "sha": Deduper._fingerprint(text), "chars": len(text)})
            groups: dict[str, list[dict]] = {}
            for d in docs:
                groups.setdefault(d["sha"], []).append(d)
            exact_dupes = [{"sha": k, "count": len(v), "files": [d["name"] for d in v]} for k, v in groups.items() if len(v) > 1]
            near = []
            for i in range(len(docs)):
                for j in range(i + 1, len(docs)):
                    a, b = docs[i], docs[j]
                    if a["sha"] == b["sha"]:
                        continue
                    if not a["text"].strip() or not b["text"].strip():
                        continue
                    ratio = difflib.SequenceMatcher(None, a["text"], b["text"]).ratio()
                    if ratio >= threshold:
                        near.append({"a": a["name"], "b": b["name"], "similarity": round(ratio, 4)})
            return {"success": True, "files": [d["name"] for d in docs], "exact_duplicates": exact_dupes, "near_duplicates": near}
        except Exception as e:
            return {"success": False, "error": str(e)}


class BriefBuilder:
    """Build a structured document brief (markdown or JSON)."""

    @staticmethod
    def build(path: str, format: str = "markdown", include_summary: bool = False, llm_summary: str | None = None) -> dict:
        try:
            doc = fitz.open(path)
            try:
                meta = doc.metadata or {}
                text = " ".join(str(doc[i].get_text()) for i in range(len(doc)))
                words = [w for w in re.split(r"\W+", text.lower()) if len(w) > 3 and w.isalpha()]
                top_terms = [w for w, _ in Counter(words).most_common(12)]
                headings = []
                for i in range(len(doc)):
                    page = doc[i]
                    for block in cast(dict[str, Any], page.get_text("dict"))["blocks"]:
                        if block.get("type") != 0:
                            continue
                        for line in block.get("lines", []):
                            spans = line.get("spans", [])
                            if spans and (spans[0]["size"] > 14 or (spans[0]["size"] > 12 and spans[0].get("flags", 0) & 2)):
                                headings.append(spans[0]["text"].strip())
                first_paragraphs = " ".join(text.split())[:1200]
                brief: dict[str, Any] = {
                    "title": meta.get("title") or Path(path).stem,
                    "author": meta.get("author"),
                    "pages": len(doc),
                    "char_count": len(text),
                    "top_terms": top_terms[:10],
                    "headings": [h for h in headings[:25] if h],
                    "excerpt": first_paragraphs,
                }
                if include_summary:
                    brief["summary"] = llm_summary or ""
                out = Path(path).with_name(f"{Path(path).stem}_brief.{'md' if format == 'markdown' else 'json'}")
                out.parent.mkdir(parents=True, exist_ok=True)
                if format == "json":
                    import json as _json

                    out.write_text(_json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
                else:
                    lines = [f"# {brief['title']}", ""]
                    if brief.get("author"):
                        lines.append(f"**Author:** {brief['author']}")
                    lines.append(f"**Pages:** {brief['pages']} · **Chars:** {brief['char_count']}")
                    if brief.get("summary"):
                        lines.extend(["", "## Summary", "", brief["summary"]])
                    lines.extend(["", "## Headings", ""])
                    lines.extend(f"- {h}" for h in brief["headings"])
                    lines.extend(["", "## Key terms", ""])
                    lines.append(", ".join(brief["top_terms"]))
                    lines.extend(["", "## Excerpt", "", brief["excerpt"], ""])
                    out.write_text("\n".join(lines), encoding="utf-8")
                return {"success": True, "path": str(out), "pages": brief["pages"], "summary": brief.get("summary")}
            finally:
                doc.close()
        except Exception as e:
            return {"success": False, "error": str(e)}
