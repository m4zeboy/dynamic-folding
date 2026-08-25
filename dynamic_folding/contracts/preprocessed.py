from __future__ import annotations

from dataclasses import dataclass, field

from dynamic_folding.contracts.file_ref import FileRef


@dataclass(frozen=True)
class PreprocessedDoc:
    file: FileRef
    text_for_embedding: str
    features: dict[str, object] = field(default_factory=dict)
