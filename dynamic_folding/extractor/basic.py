from __future__ import annotations

from dynamic_folding.contracts.extracted import ExtractedDoc
from dynamic_folding.contracts.file_ref import FileRef


def extract(file: FileRef) -> ExtractedDoc:
    """Basic metadata extractor (MVP).

    Content extraction will be added later.
    """

    md: dict[str, object] = {
        "name": file.name,
        "ext": file.ext,
        "rel_path": file.rel_path,
        "depth": file.depth,
        "size": file.size,
        "ctime": file.ctime,
        "mtime": file.mtime,
    }
    return ExtractedDoc(file=file, metadata=md, errors=[])
