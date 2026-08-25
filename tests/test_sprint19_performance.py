"""Sprint 19: per-stage timings and peak-memory instrumentation in RunResult.

See ADR 0018 (Property #4: Computational scaling) and SPEC Sprint 19.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest


def test_run_result_has_timings_field() -> None:
    """RunResult must expose a 'timings: dict[str, float]' field."""
    from dynamic_folding.contracts.run_result import RunResult

    sig = inspect.signature(RunResult)
    assert "timings" in sig.parameters, (
        "RunResult must add a 'timings' field for Sprint 19 (default empty dict)."
    )


def test_run_result_has_peak_memory_field() -> None:
    """RunResult must expose a 'peak_memory_mb: float | None' field."""
    from dynamic_folding.contracts.run_result import RunResult

    sig = inspect.signature(RunResult)
    assert "peak_memory_mb" in sig.parameters, (
        "RunResult must add a 'peak_memory_mb' field for Sprint 19 (default None)."
    )


def test_pipeline_populates_timings(tmp_path: Path) -> None:
    """Every pipeline run must record per-stage wall-clock in result.timings."""
    from dynamic_folding.core.pipeline import run_pipeline

    root = tmp_path / "perf"
    root.mkdir()
    (root / "a.txt").write_text("hello")
    (root / "b.txt").write_text("world")

    result = run_pipeline(root)
    assert hasattr(result, "timings"), "RunResult.timings missing"
    assert isinstance(result.timings, dict)

    expected = {"scanner", "extractor", "preprocess", "embedding", "clustering", "naming", "proposal"}
    missing = expected - set(result.timings.keys())
    assert not missing, f"Missing stage timings: {sorted(missing)}"

    for stage, t in result.timings.items():
        assert t >= 0, f"Stage '{stage}' has negative timing {t}"


def test_pipeline_peak_memory_when_available(tmp_path: Path) -> None:
    """When the helper returns a value, peak_memory_mb is a positive float."""
    try:
        import psutil  # noqa: F401
    except ImportError:
        pytest.skip("psutil not installed; covered by separate test")

    from dynamic_folding.core.pipeline import run_pipeline

    root = tmp_path / "mem"
    root.mkdir()
    (root / "f.txt").write_text("data")

    result = run_pipeline(root)
    assert result.peak_memory_mb is not None
    assert result.peak_memory_mb > 0


def test_pipeline_graceful_when_peak_memory_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If peak memory cannot be measured, peak_memory_mb is None and no crash."""
    from dynamic_folding.core import pipeline as p

    if not hasattr(p, "_get_peak_memory_mb"):
        pytest.fail(
            "pipeline must expose _get_peak_memory_mb() so tests can simulate "
            "an environment without psutil."
        )

    monkeypatch.setattr(p, "_get_peak_memory_mb", lambda: None)

    root = tmp_path / "no_mem"
    root.mkdir()
    (root / "f.txt").write_text("data")

    result = p.run_pipeline(root)
    assert result.peak_memory_mb is None


def test_run_result_to_dict_includes_new_fields(tmp_path: Path) -> None:
    """RunResult.to_dict must surface timings + peak_memory_mb for the JSON output."""
    from dynamic_folding.core.pipeline import run_pipeline

    root = tmp_path / "to_dict"
    root.mkdir()
    (root / "f.txt").write_text("x")

    result = run_pipeline(root)
    d = result.to_dict()
    assert "timings" in d, "to_dict must include timings"
    assert "peak_memory_mb" in d, "to_dict must include peak_memory_mb"
    assert isinstance(d["timings"], dict)
