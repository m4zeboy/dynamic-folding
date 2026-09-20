from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FolderNode:
    """A recursive node in the structure proposal."""
    name: str
    files: list[str] = field(default_factory=list)  # Relative paths directly in this folder
    subfolders: list[FolderNode] = field(default_factory=list)
    name_match: float | None = None
    display_name: str | None = None

    def to_dict(self) -> dict:
        d: dict = {
            "name": self.name,
            "files": self.files,
            "subfolders": [s.to_dict() for s in self.subfolders],
            "name_match": self.name_match,
        }
        if self.display_name is not None:
            d["display_name"] = self.display_name
        return d


@dataclass
class StructureProposal:
    """The final result of the intelligence pipeline (Contract v4).

    v4 (2026-06-07): removed the user-facing confidence signal — `FolderNode.cohesion`
    and `StructureProposal.cohesion_score`. Silhouette is now an evaluation-only
    instrument (see ADR 0035); it is no longer carried on the product contract.
    """
    root: str
    folders: list[FolderNode] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    contracts_version: int = 4

    def to_dict(self) -> dict:
        return {
            "contracts_version": self.contracts_version,
            "root": self.root,
            "folders": [f.to_dict() for f in self.folders],
            "orphans": self.orphans,
            "notes": self.notes,
        }
