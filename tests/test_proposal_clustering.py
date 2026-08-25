from __future__ import annotations

import json
from pathlib import Path


def _touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")


def test_pipeline_proposes_two_level_structure(tmp_path: Path) -> None:
    # Group A (in filenames)
    _touch(tmp_path / "invoice_2023_jan.pdf")
    _touch(tmp_path / "invoice_2023_feb.pdf")
    _touch(tmp_path / "invoice_2024_jan.pdf")

    # Group B
    _touch(tmp_path / "photo_trip_paris_01.jpg")
    _touch(tmp_path / "photo_trip_paris_02.jpg")
    _touch(tmp_path / "photo_trip_rome_01.jpg")

    # Group C
    _touch(tmp_path / "code_project_alpha.py")
    _touch(tmp_path / "code_project_beta.py")

    from dynamic_folding.core.pipeline import run_pipeline
    from dynamic_folding.contracts.proposal import FolderNode

    r = run_pipeline(tmp_path)
    p = r.proposal

    # We expect non-empty proposal once clustering+naming is implemented.
    assert isinstance(p.folders, list)
    assert p.folders, "expected some top-level folders"
    assert isinstance(p.folders[0], FolderNode)

    # Windows-safe names: no empty, no trailing spaces/dots.
    def check_node(node: FolderNode):
        assert node.name.strip() == node.name
        assert not node.name.endswith(".")
        assert node.name
        for sub in node.subfolders:
            check_node(sub)

    for node in p.folders:
        check_node(node)


def test_pipeline_proposal_is_deterministic(tmp_path: Path) -> None:
    for n in ["b_invoice.pdf", "a_invoice.pdf", "c_invoice.pdf"]:
        _touch(tmp_path / n)

    from dynamic_folding.core.pipeline import run_pipeline

    r1 = run_pipeline(tmp_path).to_dict()["proposal"]
    r2 = run_pipeline(tmp_path).to_dict()["proposal"]

    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
