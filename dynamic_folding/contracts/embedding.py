from __future__ import annotations

from dataclasses import dataclass

from dynamic_folding.contracts.file_ref import FileRef


@dataclass(frozen=True)
class EmbeddingRecord:
    file: FileRef
    vector: list[float]
    model_id: str
    content_hash: str
