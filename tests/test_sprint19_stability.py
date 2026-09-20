"""Sprint 19: stability analyzer (pair-co-occurrence over perturbed runs).

See ADR 0018 (Property #2: Stability) and SPEC Sprint 19 for behavioral
contract. CONTRACTS.md defines StabilityReport.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def test_stability_report_dto_exists() -> None:
    try:
        from dynamic_folding.contracts.stability import StabilityReport
    except ImportError:
        pytest.fail("dynamic_folding.contracts.stability.StabilityReport must exist")

    rpt = StabilityReport(
        root="/x",
        runs=5,
        perturbation=0.1,
        seed=0,
        pair_co_occurrence=0.85,
        evaluable_pairs=42,
        notes=[],
    )
    assert rpt.contracts_version == 2
    assert rpt.pair_co_occurrence == 0.85
    assert rpt.runs == 5


def test_stability_report_serializes() -> None:
    from dynamic_folding.contracts.stability import StabilityReport

    rpt = StabilityReport(
        root="/x",
        runs=3,
        perturbation=0.1,
        seed=0,
        pair_co_occurrence=0.5,
        evaluable_pairs=10,
        notes=["test"],
    )
    d = rpt.to_dict()
    assert d["contracts_version"] == 2
    assert d["pair_co_occurrence"] == 0.5
    assert d["runs"] == 3
    assert d["evaluable_pairs"] == 10
    assert d["notes"] == ["test"]


def test_stability_no_perturbation_returns_one(tmp_path: Path) -> None:
    """perturbation=0 means identical inputs each run → pair_co_occurrence = 1.0."""
    try:
        from dynamic_folding.core.stability import compute_stability
    except ImportError:
        pytest.fail("dynamic_folding.core.stability.compute_stability must exist")

    root = tmp_path / "no_pert"
    root.mkdir()
    for i in range(8):
        (root / f"file_{i}.txt").write_text(f"content {i}")

    report = compute_stability(root, runs=3, perturbation=0.0, seed=0)
    assert report.pair_co_occurrence == 1.0
    assert report.evaluable_pairs > 0


def test_stability_runs_lt_2_disabled(tmp_path: Path) -> None:
    """runs<2 cannot measure stability; must report 1.0 with an explanatory note."""
    from dynamic_folding.core.stability import compute_stability

    root = tmp_path / "single_run"
    root.mkdir()
    for i in range(5):
        (root / f"f{i}.txt").write_text(str(i))

    report = compute_stability(root, runs=1, perturbation=0.1, seed=0)
    assert report.pair_co_occurrence == 1.0
    assert any("runs" in n.lower() for n in report.notes), (
        "Expected a note explaining stability requires >=2 runs"
    )


def test_stability_deterministic(tmp_path: Path) -> None:
    """Same seed → identical pair_co_occurrence."""
    from dynamic_folding.core.stability import compute_stability

    root = tmp_path / "det"
    root.mkdir()
    for i in range(12):
        (root / f"d{i}.txt").write_text(f"data {i}")

    r1 = compute_stability(root, runs=3, perturbation=0.2, seed=7)
    r2 = compute_stability(root, runs=3, perturbation=0.2, seed=7)
    assert r1.pair_co_occurrence == r2.pair_co_occurrence
    assert r1.evaluable_pairs == r2.evaluable_pairs


def test_stability_co_occurrence_in_unit_interval(tmp_path: Path) -> None:
    from dynamic_folding.core.stability import compute_stability

    root = tmp_path / "interval"
    root.mkdir()
    for i in range(15):
        (root / f"x{i}.txt").write_text(f"text content {i}")

    report = compute_stability(root, runs=4, perturbation=0.15, seed=0)
    assert 0.0 <= report.pair_co_occurrence <= 1.0
    assert 0.0 <= report.perturbation <= 0.5
