from __future__ import annotations

from pathlib import Path

from dynamic_folding.core.pipeline import run_pipeline
from dynamic_folding.render.tree import render_tree


def test_pipeline_returns_proposal(tmp_path: Path) -> None:
    r = run_pipeline(tmp_path)
    assert r.contracts_version == 2
    assert r.root
    assert r.proposal.contracts_version == 4
    assert r.proposal.root


def test_render_tree_is_deterministic(tmp_path: Path) -> None:
    r1 = run_pipeline(tmp_path)
    r2 = run_pipeline(tmp_path)
    assert render_tree(r1.proposal) == render_tree(r2.proposal)
