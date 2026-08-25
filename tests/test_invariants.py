from __future__ import annotations

from pathlib import Path


def _touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")


def test_each_scanned_file_is_placed_exactly_once(tmp_path: Path) -> None:
    _touch(tmp_path / "invoice_2023_jan.pdf")
    _touch(tmp_path / "invoice_2023_feb.pdf")
    _touch(tmp_path / "photo_trip_paris_01.jpg")
    _touch(tmp_path / "code_project_alpha.py")

    from dynamic_folding.core.pipeline import run_pipeline
    from dynamic_folding.contracts.proposal import FolderNode

    r = run_pipeline(tmp_path)
    file_rels = sorted([fr.rel_path for fr in r.files if not fr.is_dir], key=str.casefold)

    placed: list[str] = []
    def collect_files(nodes: list[FolderNode]):
        for n in nodes:
            placed.extend(n.files)
            collect_files(n.subfolders)
    
    collect_files(r.proposal.folders)
    placed.extend(r.proposal.orphans)

    assert sorted(placed, key=str.casefold) == file_rels


def test_validate_proposal_reports_duplicates_and_unknowns() -> None:
    from dynamic_folding.contracts.file_ref import FileRef
    from dynamic_folding.contracts.proposal import StructureProposal, FolderNode
    from dynamic_folding.core.validate import validate_proposal

    files = [
        FileRef(
            path="C:/x/a.txt",
            rel_path="a.txt",
            is_dir=False,
            depth=0,
            name="a.txt",
            ext="txt",
            size=1,
            ctime=None,
            mtime=None,
        ),
        FileRef(
            path="C:/x/b.txt",
            rel_path="b.txt",
            is_dir=False,
            depth=0,
            name="b.txt",
            ext="txt",
            size=1,
            ctime=None,
            mtime=None,
        ),
    ]

    p = StructureProposal(
        root="C:/x",
        folders=[
            FolderNode(name="F1", files=["a.txt"]),
            FolderNode(name="F2", files=["a.txt", "missing.txt"]),
        ],
        orphans=[],
        notes=[],
    )

    warnings = validate_proposal(p, files)
    assert any("duplicate" in w.lower() for w in warnings)
    assert any("unknown" in w.lower() for w in warnings)
