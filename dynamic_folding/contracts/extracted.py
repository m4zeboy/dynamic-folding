from __future__ import annotations

from dataclasses import dataclass, field

from dynamic_folding.contracts.file_ref import FileRef


@dataclass(frozen=True)
class ExtractedDoc:
    file: FileRef
    metadata: dict[str, object]
    errors: list[str] = field(default_factory=list)
