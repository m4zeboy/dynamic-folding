from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FileRef:
    path: str
    rel_path: str
    is_dir: bool
    depth: int

    name: str
    ext: str

    size: int | None
    ctime: float | None
    mtime: float | None
