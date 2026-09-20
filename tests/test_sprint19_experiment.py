"""Sprint 19 — Step 6b: experiment orchestration tests.

These tests verify the experiment runner's flow without invoking the real
pipeline. `run_characterize` and `run_analyze` are monkey-patched so we
can assert on call patterns and orchestration behavior.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


def _make_corpus(parent: Path, name: str, n_files: int) -> Path:
    p = parent / name
    p.mkdir(parents=True)
    for i in range(n_files):
        (p / f"file_{i}.txt").write_text(f"content {i}")
    return p


def test_experiment_runs_spine_once_per_corpus_and_sensitivity_on_smallest(
    tmp_path: Path,
) -> None:
    from dynamic_folding.core import experiment as exp

    datasets = tmp_path / "datasets"
    datasets.mkdir()
    _make_corpus(datasets, "A", 3)
    _make_corpus(datasets, "B", 5)
    _make_corpus(datasets, "C", 7)

    captured: list[dict[str, Any]] = []
    with patch.object(
        exp,
        "run_characterize",
        side_effect=lambda root, **kw: captured.append({"root": root, **kw}),
    ):
        summary = exp.run_experiment(datasets, run_analysis=False)

    spine_calls = [c for c in captured if c["perturbation"] == 0.10]
    sens_calls = [c for c in captured if c["perturbation"] != 0.10]
    assert len(spine_calls) == 3
    sens_corpora = {c["root"].name for c in sens_calls}
    assert sens_corpora == {"A"}
    sens_perts = sorted(c["perturbation"] for c in sens_calls)
    assert sens_perts == [0.05, 0.20]
    assert summary["sensitivity_corpus"] == "A"
    assert len(summary["spine_runs"]) == 3
    assert len(summary["sensitivity_runs"]) == 2
    assert summary["failures"] == []


def test_experiment_picks_smallest_corpus_by_default(tmp_path: Path) -> None:
    from dynamic_folding.core import experiment as exp

    datasets = tmp_path / "datasets"
    datasets.mkdir()
    _make_corpus(datasets, "Big", 10)
    _make_corpus(datasets, "Small", 2)

    captured: list[dict[str, Any]] = []
    with patch.object(
        exp,
        "run_characterize",
        side_effect=lambda root, **kw: captured.append({"root": root, **kw}),
    ):
        summary = exp.run_experiment(datasets, run_analysis=False)

    assert summary["sensitivity_corpus"] == "Small"
    sens_calls = [c for c in captured if c["perturbation"] != 0.10]
    assert all(c["root"].name == "Small" for c in sens_calls)


def test_experiment_respects_sensitivity_corpus_override(tmp_path: Path) -> None:
    from dynamic_folding.core import experiment as exp

    datasets = tmp_path / "datasets"
    datasets.mkdir()
    _make_corpus(datasets, "A", 3)
    _make_corpus(datasets, "B", 5)

    with patch.object(
        exp, "run_characterize", side_effect=lambda root, **kw: None
    ):
        summary = exp.run_experiment(
            datasets, sensitivity_corpus="B", run_analysis=False
        )
    assert summary["sensitivity_corpus"] == "B"


def test_experiment_continues_on_failure(tmp_path: Path) -> None:
    from dynamic_folding.core import experiment as exp

    datasets = tmp_path / "datasets"
    datasets.mkdir()
    _make_corpus(datasets, "A", 3)
    _make_corpus(datasets, "B", 5)

    def stub(root, **kw):
        if root.name == "A" and kw["perturbation"] == 0.10:
            raise RuntimeError("boom")
        return None

    with patch.object(exp, "run_characterize", side_effect=stub):
        summary = exp.run_experiment(datasets, run_analysis=False)

    assert len(summary["failures"]) >= 1
    a_failure = next(
        f for f in summary["failures"] if f.get("corpus") == "A"
    )
    assert "boom" in a_failure["error"]
    assert len(summary["spine_runs"]) == 1
    assert summary["spine_runs"][0]["corpus"] == "B"


def test_experiment_skips_analysis_when_disabled(tmp_path: Path) -> None:
    from dynamic_folding.core import experiment as exp

    datasets = tmp_path / "datasets"
    datasets.mkdir()
    _make_corpus(datasets, "A", 3)

    analyze_called: list[bool] = []
    with patch.object(exp, "run_characterize", side_effect=lambda root, **kw: None):
        with patch.object(
            exp,
            "run_analyze",
            side_effect=lambda *a, **kw: analyze_called.append(True),
        ):
            summary = exp.run_experiment(datasets, run_analysis=False)
    assert summary["report_path"] is None
    assert analyze_called == []


def test_experiment_runs_analysis_when_enabled(tmp_path: Path) -> None:
    from dynamic_folding.core import experiment as exp

    datasets = tmp_path / "datasets"
    datasets.mkdir()
    _make_corpus(datasets, "A", 3)

    fake_report = tmp_path / "report.md"
    with patch.object(exp, "run_characterize", side_effect=lambda root, **kw: None):
        with patch.object(exp, "run_analyze", return_value=fake_report):
            summary = exp.run_experiment(datasets, run_analysis=True)
    assert summary["report_path"] == str(fake_report)


def test_experiment_errors_when_no_subdirs(tmp_path: Path) -> None:
    from dynamic_folding.core import experiment as exp

    datasets = tmp_path / "datasets"
    datasets.mkdir()
    with pytest.raises(ValueError, match="no valid corpora"):
        exp.run_experiment(datasets, run_analysis=False)
