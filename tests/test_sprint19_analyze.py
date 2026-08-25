"""Sprint 19 — Step 6: analysis script tests.

Synthesizes characterize_*.json fixtures and verifies the report renders.
See docs/learning/02-experimental-scope.md for the experimental design.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


def _write_fake_json(
    out_dir: Path,
    *,
    corpus_root: str,
    perturbation: float,
    stability: float,
    sil_real: float | None,
    sil_random: float | None,
    n: int,
    timings: dict[str, float] | None = None,
    peak_mem: float | None = 234.5,
) -> Path:
    timings = timings or {"scanner": 0.01, "extractor": 0.05, "embedding": 1.5, "proposal": 0.3}
    data: dict[str, Any] = {
        "contracts_version": 2,
        "root": corpus_root,
        "corpus_metadata": {"n_files": n, "n_embedded": n, "root": corpus_root},
        "config": {},
        "structure": {"silhouette_real": sil_real, "silhouette_random": sil_random, "k": 3},
        "stability": {
            "contracts_version": 2,
            "root": corpus_root,
            "runs": 5,
            "perturbation": perturbation,
            "seed": 0,
            "pair_co_occurrence": stability,
            "evaluable_pairs": (n * (n - 1)) // 2,
            "notes": [],
        },
        "performance": {
            "timings": dict(timings),
            "peak_memory_mb": peak_mem,
        },
        "notes": [],
    }
    fname = f"characterize_{int(perturbation * 1000):04d}_{Path(corpus_root).name}.json"
    p = out_dir / fname
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p


def test_load_results_empty_dir(tmp_path: Path) -> None:
    from dynamic_folding.core.analyze import load_results

    results = load_results(tmp_path)
    assert results == []


def test_run_analyze_raises_when_no_jsons(tmp_path: Path) -> None:
    from dynamic_folding.core.analyze import run_analyze

    with pytest.raises(ValueError, match="no characterize_"):
        run_analyze(tmp_path, output_dir=tmp_path / "out")


def test_run_analyze_raises_when_dir_missing(tmp_path: Path) -> None:
    from dynamic_folding.core.analyze import run_analyze

    with pytest.raises(FileNotFoundError):
        run_analyze(tmp_path / "does_not_exist", output_dir=tmp_path / "out")


def test_spine_table_renders_basic(tmp_path: Path) -> None:
    from dynamic_folding.core.analyze import group_by_corpus, load_results, render_spine_table

    _write_fake_json(tmp_path, corpus_root="/datasets/A", perturbation=0.10,
                     stability=0.85, sil_real=0.250, sil_random=-0.050, n=8)
    _write_fake_json(tmp_path, corpus_root="/datasets/B", perturbation=0.10,
                     stability=0.78, sil_real=0.180, sil_random=0.010, n=12)

    by_corpus = group_by_corpus(load_results(tmp_path))
    md = render_spine_table(by_corpus)

    assert "Corpus" in md
    assert "n files" in md
    assert "0.250" in md
    assert "0.180" in md
    assert "0.850" in md
    assert "0.780" in md


def test_sensitivity_table_appears_only_when_multiple_perturbations(tmp_path: Path) -> None:
    from dynamic_folding.core.analyze import group_by_corpus, load_results, render_sensitivity_tables

    # corpus A: only one perturbation level -> no sensitivity row for it
    _write_fake_json(tmp_path, corpus_root="/datasets/A", perturbation=0.10,
                     stability=0.85, sil_real=0.25, sil_random=0.0, n=8)
    # corpus B: three perturbation levels -> sensitivity table for B
    _write_fake_json(tmp_path, corpus_root="/datasets/B", perturbation=0.05,
                     stability=0.95, sil_real=0.25, sil_random=0.0, n=10)
    _write_fake_json(tmp_path, corpus_root="/datasets/B", perturbation=0.10,
                     stability=0.85, sil_real=0.25, sil_random=0.0, n=10)
    _write_fake_json(tmp_path, corpus_root="/datasets/B", perturbation=0.20,
                     stability=0.65, sil_real=0.25, sil_random=0.0, n=10)

    by_corpus = group_by_corpus(load_results(tmp_path))
    md = render_sensitivity_tables(by_corpus)

    assert md is not None
    assert "Sensitivity: B" in md
    assert "Sensitivity: A" not in md
    assert "0.05" in md and "0.10" in md and "0.20" in md
    assert "0.950" in md and "0.650" in md


def test_run_analyze_writes_report_md(tmp_path: Path) -> None:
    from dynamic_folding.core.analyze import run_analyze

    _write_fake_json(tmp_path, corpus_root="/datasets/A", perturbation=0.10,
                     stability=0.85, sil_real=0.25, sil_random=0.0, n=8)

    out_dir = tmp_path / "out"
    report = run_analyze(tmp_path, output_dir=out_dir, skip_figures=True)

    assert report.exists()
    assert report.name == "report.md"
    content = report.read_text(encoding="utf-8")
    assert "Spine experiment" in content
    assert "0.850" in content


def test_handles_none_silhouette_gracefully(tmp_path: Path) -> None:
    from dynamic_folding.core.analyze import group_by_corpus, load_results, render_spine_table

    _write_fake_json(tmp_path, corpus_root="/datasets/A", perturbation=0.10,
                     stability=1.0, sil_real=None, sil_random=None, n=2)

    by_corpus = group_by_corpus(load_results(tmp_path))
    md = render_spine_table(by_corpus)

    assert "n/a" in md
