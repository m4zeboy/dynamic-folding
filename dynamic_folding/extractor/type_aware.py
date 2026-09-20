from __future__ import annotations

import logging
from typing import Any

from dynamic_folding.contracts.extracted import ExtractedDoc
from dynamic_folding.contracts.file_ref import FileRef

logger = logging.getLogger(__name__)

# --- Optional Parsers ---

def _iter_outline_titles(outline: Any):
    """Depth-first traversal of a pypdf outline yielding decoded titles.

    Entries may be Destination-like objects with `.title`, or nested lists
    representing children. Entries whose titles fail to decode are skipped.
    """
    try:
        items = iter(outline)
    except TypeError:
        return
    for entry in items:
        if isinstance(entry, list):
            yield from _iter_outline_titles(entry)
            continue
        try:
            title = entry.title
        except Exception:
            continue
        if not title:
            continue
        try:
            text = str(title).strip()
        except Exception:
            continue
        if text:
            yield text


class PdfParser:
    """Extracts metadata and a smart structural snippet from PDF files.

    Priority block (in order): /Subject, /Keywords, outline titles (DFS).
    Backfilled with body text from the first 3 pages under `snippet_size`.
    """
    def __init__(self):
        try:
            import pypdf
            self._pypdf = pypdf
        except ImportError:
            raise ImportError("pypdf not installed")

    def extract(self, file_path: str, snippet_size: int) -> dict[str, Any]:
        data: dict[str, Any] = {
            "snippet": "",
            "title": "",
            "author": "",
            "subject": "",
            "keywords": "",
        }
        try:
            reader = self._pypdf.PdfReader(file_path)
            meta = reader.metadata or {}
            data["title"] = meta.get("/Title", "") or ""
            data["author"] = meta.get("/Author", "") or ""
            data["subject"] = meta.get("/Subject", "") or ""
            data["keywords"] = meta.get("/Keywords", "") or ""

            priority_parts: list[str] = []
            if data["subject"]:
                priority_parts.append(str(data["subject"]))
            if data["keywords"]:
                priority_parts.append(str(data["keywords"]))

            outline = getattr(reader, "outline", None)
            if outline is not None:
                for title in _iter_outline_titles(outline):
                    priority_parts.append(title)

            priority_text = "\n".join(priority_parts)
            snippet = priority_text[:snippet_size]

            if len(snippet) < snippet_size:
                remaining = snippet_size - len(snippet)
                pages_to_read = reader.pages[:3]
                body_buf: list[str] = []
                for page in pages_to_read:
                    if remaining <= 0:
                        break
                    text = page.extract_text() or ""
                    if not text:
                        continue
                    sep = "\n" if (snippet or body_buf) else ""
                    take = remaining - len(sep)
                    if take <= 0:
                        break
                    chunk = text[:take]
                    body_buf.append(sep + chunk)
                    remaining -= len(sep) + len(chunk)
                if body_buf:
                    snippet = (snippet + "".join(body_buf))[:snippet_size]

            data["snippet"] = snippet
        except Exception as e:
            logger.warning(f"Failed to parse PDF {file_path}: {e}")
        return data


class ImageParser:
    """Extracts EXIF metadata from image files using Pillow."""
    def __init__(self):
        try:
            from PIL import Image
            self._Image = Image
        except ImportError:
            raise ImportError("Pillow not installed")

    def extract(self, file_path: str) -> dict[str, Any]:
        data: dict[str, Any] = {"datetime": "", "make": "", "model": "", "software": ""}
        try:
            with self._Image.open(file_path) as img:
                exif = img.getexif()
                if exif:
                    # Tags: 0x0132: DateTime, 0x010f: Make, 0x0110: Model, 0x0131: Software
                    data["datetime"] = exif.get(0x0132, "")
                    data["make"] = exif.get(0x010f, "")
                    data["model"] = exif.get(0x0110, "")
                    data["software"] = exif.get(0x0131, "")
        except Exception as e:
            logger.warning(f"Failed to parse Image {file_path}: {e}")
        return data


class DocxParser:
    """Extracts metadata and smart snippet from DOCX files using python-docx."""
    def __init__(self):
        try:
            import docx
            self._docx = docx
        except ImportError as e:
            print("DOCX IMPORT ERROR:", e)
            raise ImportError("python-docx not installed")

    def extract(self, file_path: str, snippet_size: int) -> dict[str, Any]:
        data: dict[str, Any] = {"snippet": "", "title": "", "author": ""}
        try:
            doc = self._docx.Document(file_path)
            if hasattr(doc, "core_properties"):
                data["title"] = doc.core_properties.title or ""
                data["author"] = doc.core_properties.author or ""
            
            priority_texts = []
            normal_texts = []
            
            for para in getattr(doc, "paragraphs", []):
                text = para.text.strip() if hasattr(para, "text") else ""
                if not text:
                    continue
                    
                style_name = ""
                if hasattr(para, "style") and hasattr(para.style, "name"):
                    style_name = para.style.name or ""
                
                if style_name.startswith(("Heading", "Title")):
                    priority_texts.append(text)
                else:
                    normal_texts.append(text)
            
            combined_text = "\n".join(priority_texts)
            if len(combined_text) < snippet_size and normal_texts:
                if combined_text:
                    combined_text += "\n"
                combined_text += "\n".join(normal_texts)
                
            data["snippet"] = combined_text[:snippet_size]
        except Exception as e:
            logger.warning(f"Failed to parse DOCX {file_path}: {e}")
        return data


class PptxParser:
    """Extracts metadata and smart snippet from PPTX files using python-pptx."""
    def __init__(self):
        try:
            import pptx
            self._pptx = pptx
        except ImportError:
            raise ImportError("python-pptx not installed")

    def extract(self, file_path: str, snippet_size: int) -> dict[str, Any]:
        data: dict[str, Any] = {"snippet": "", "title": ""}
        try:
            prs = self._pptx.Presentation(file_path)
            if hasattr(prs, "core_properties"):
                data["title"] = prs.core_properties.title or ""
            
            # PP_PLACEHOLDER.TITLE is 1, CENTER_TITLE is 3
            TITLE_TYPES = (1, 3) 
            
            priority_texts = []
            normal_texts = []
            
            for slide in getattr(prs, "slides", []):
                for shape in getattr(slide, "shapes", []):
                    if not getattr(shape, "has_text_frame", False):
                        continue
                    text = shape.text.strip() if hasattr(shape, "text") else ""
                    if not text:
                        continue
                        
                    is_title = False
                    if getattr(shape, "is_placeholder", False):
                        ph_format = getattr(shape, "placeholder_format", None)
                        ph_type = getattr(ph_format, "type", None)
                        if ph_type in TITLE_TYPES:
                            is_title = True
                            
                    if is_title:
                        priority_texts.append(text)
                    else:
                        normal_texts.append(text)
            
            combined_text = "\n".join(priority_texts)
            if len(combined_text) < snippet_size and normal_texts:
                if combined_text:
                    combined_text += "\n"
                combined_text += "\n".join(normal_texts)
                
            data["snippet"] = combined_text[:snippet_size]
        except Exception as e:
            logger.warning(f"Failed to parse PPTX {file_path}: {e}")
        return data


# --- Core Logic ---

def extract_text_snippet(file_path: str, snippet_size: int) -> str:
    """Read a small snippet of text with robust encoding fallback."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(snippet_size)
    except Exception:
        try:
            with open(file_path, "r", encoding="latin-1", errors="ignore") as f:
                return f.read(snippet_size)
        except Exception:
            return ""


def extract(file: FileRef, cfg: dict[str, Any] | None = None) -> ExtractedDoc:
    """Type-aware extractor dispatcher."""
    cfg = cfg or {}
    # Default mirrors the single source of truth in config.py::get_system_defaults()
    # (scanner.snippet_size = 4096). A divergent 1024 here previously truncated
    # snippets even when the pipeline forgot to pass the configured value. See ADR 0036.
    snippet_size = int(cfg.get("snippet_size", 4096))
    
    md: dict[str, Any] = {
        "name": file.name,
        "ext": file.ext,
        "rel_path": file.rel_path,
        "depth": file.depth,
        "size": file.size,
        "ctime": file.ctime,
        "mtime": file.mtime,
        "snippet": "",
    }
    errors: list[str] = []

    ext = "." + file.ext.lower().lstrip(".")
    text_exts = {".txt", ".md", ".py", ".json", ".csv", ".log", ".ini", ".toml", ".yml", ".yaml"}

    try:
        if ext in text_exts:
            md["snippet"] = extract_text_snippet(file.path, snippet_size)
        elif ext == ".pdf":
            try:
                pdf_data = PdfParser().extract(file.path, snippet_size)
                md.update(pdf_data)
            except ImportError:
                pass # Graceful fallback
        elif ext in {".jpg", ".jpeg", ".png"}:
            try:
                img_data = ImageParser().extract(file.path)
                md.update(img_data)
            except ImportError:
                pass # Graceful fallback
        elif ext == ".docx":
            try:
                docx_data = DocxParser().extract(file.path, snippet_size)
                md.update(docx_data)
            except ImportError:
                pass # Graceful fallback
        elif ext == ".pptx":
            try:
                pptx_data = PptxParser().extract(file.path, snippet_size)
                md.update(pptx_data)
            except ImportError:
                pass # Graceful fallback
    except Exception as e:
        errors.append(f"Failed to extract from {file.name}: {str(e)}")

    return ExtractedDoc(file=file, metadata=md, errors=errors)
