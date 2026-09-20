from __future__ import annotations

from collections import Counter

from dynamic_folding.contracts.file_ref import FileRef
from dynamic_folding.contracts.proposal import StructureProposal


def validate_proposal(p: StructureProposal, files: list[FileRef]) -> list[str]:
    """Return human-readable warnings if proposal violates basic invariants."""

    known = {f.rel_path for f in files if not f.is_dir}

    def collect_files(nodes: list[FolderNode]) -> list[str]:
        out = []
        for n in nodes:
            out.extend(n.files)
            out.extend(collect_files(n.subfolders))
        return out

    placed = collect_files(p.folders)
    placed.extend(p.orphans)

    c = Counter(placed)
    dups = sorted([k for k, v in c.items() if v > 1], key=str.casefold)
    unknowns = sorted([x for x in placed if x not in known], key=str.casefold)
    missing = sorted([x for x in known if x not in c], key=str.casefold)

    warnings: list[str] = []
    if dups:
        warnings.append(f"Duplicate file placements detected: {dups[:10]}")
    if unknowns:
        warnings.append(f"Unknown file references in proposal: {unknowns[:10]}")
    if missing:
        warnings.append(f"Some files were not placed by proposal: {missing[:10]}")
    return warnings
