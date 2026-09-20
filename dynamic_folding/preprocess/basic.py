from __future__ import annotations

import re
from pathlib import Path

from dynamic_folding.contracts.extracted import ExtractedDoc
from dynamic_folding.contracts.preprocessed import PreprocessedDoc


def preprocess(doc: ExtractedDoc, *, template: str) -> PreprocessedDoc:
    """Preprocess metadata into an embedding-ready text.

    Keep deterministic and configuration-driven.
    """

    fr = doc.file
    stem = Path(fr.name).stem
    values = {
        "name": fr.name,
        "stem": stem,
        "ext": fr.ext,
        "rel_path": fr.rel_path,
        "depth": fr.depth,
        "size": fr.size if fr.size is not None else "",
    }
    # Add all extracted metadata (snippet, title, etc.)
    values.update(doc.metadata)

    # Note: previous versions computed a `best_title` field that prioritized
    # the document's internal title over the filename stem (ADR 0011, point 2).
    # That behaviour was retired by ADR 0025 — the template now emits both
    # `{stem}` and `{title}` in distinct slots so the embedder sees both
    # signals without one being silently dropped.

    # Use a safe formatter that replaces missing keys with empty strings
    class SafeDict(dict):
        def __missing__(self, key):
            return ""

    safe_values = SafeDict(values)
    text = template.format_map(safe_values)

    # Remove [TAG]: slots where the value rendered to empty string — these add
    # noise to the embedding input. A slot is empty when its colon is followed
    # only by whitespace before the next [TAG] or end of string.
    text = re.sub(r'\[[^\]]+\]:\s+(?=\[|$)', '', text)

    # Normalize whitespace.
    text = " ".join(str(text).split())
    return PreprocessedDoc(file=fr, text_for_embedding=text, features={})
