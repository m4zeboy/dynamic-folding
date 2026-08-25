"""Sprint 19 — Step 6b: one-shot experiment runner.

Auto-discovers corpora as immediate subdirectories of a parent path and
runs the full spine + sensitivity matrix in a single call. Optionally
calls the analysis stage to produce the chapter Markdown + figures.

See `docs/learning/02-experimental-scope.md` for the experimental design
this module orchestrates.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from dynamic_folding.core.analyze import run_analyze
from dynamic_folding.core.characterize import run_characterize


def _is_valid_corpus(p: Path) -> bool:
    if not p.is_dir() or p.name.startswith("."):
        return False
    return any(child.is_file() for child in p.rglob("*"))


def _count_files(p: Path) -> int:
    return sum(1 for child in p.rglob("*") if child.is_file())


def _discover_corpora(datasets_dir: Path) -> list[Path]:
    if not datasets_dir.exists():
        raise FileNotFoundError(f"datasets directory not found: {datasets_dir}")
    if not datasets_dir.is_dir():
        raise NotADirectoryError(f"datasets path is not a directory: {datasets_dir}")
    corpora = sorted(
        (p for p in datasets_dir.iterdir() if _is_valid_corpus(p)),
        key=lambda p: p.name,
    )
    if not corpora:
        raise ValueError(
            f"no valid corpora found as immediate subdirectories of {datasets_dir} "
            "(needs at least one non-hidden, non-empty subdirectory)"
        )
    return corpora


def _select_sensitivity_corpus(corpora: list[Path], requested: str | None) -> Path:
    if requested is None:
        return min(corpora, key=_count_files)
    matches = [c for c in corpora if c.name == requested]
    if not matches:
        names = sorted(c.name for c in corpora)
        raise ValueError(
            f"sensitivity corpus '{requested}' not found among "
            f"discovered corpora: {names}"
        )
    return matches[0]


def _run_one(
    corpus: Path,
    *,
    perturbation: float,
    seed: int,
    output_dir: Path,
    config_path: Path | None,
    label: str,
) -> dict[str, Any]:
    print(
        f"[{label}] {corpus.name} @ perturbation={perturbation:.2f} ...",
        file=sys.stderr,
        flush=True,
    )
    t0 = time.perf_counter()
    try:
        run_characterize(
            corpus,
            output_dir=output_dir,
            config_path=config_path,
            perturbation=perturbation,
            seed=seed,
        )
        elapsed = time.perf_counter() - t0
        print(
            f"[{label}] {corpus.name} @ {perturbation:.2f} done in {elapsed:.1f}s",
            file=sys.stderr,
            flush=True,
        )
        return {
            "stage": label,
            "corpus": corpus.name,
            "perturbation": perturbation,
            "elapsed_seconds": elapsed,
            "ok": True,
        }
    except Exception as e:
        elapsed = time.perf_counter() - t0
        print(
            f"[{label}] {corpus.name} @ {perturbation:.2f} FAILED: {e}",
            file=sys.stderr,
            flush=True,
        )
        return {
            "stage": label,
            "corpus": corpus.name,
            "perturbation": perturbation,
            "elapsed_seconds": elapsed,
            "error": str(e),
            "ok": False,
        }


def run_experiment(
    datasets_dir: Path,
    *,
    config_path: Path | None = None,
    sensitivity_corpus: str | None = None,
    perturbations: list[float] | None = None,
    spine_perturbation: float = 0.10,
    seed: int = 0,
    output_dir: Path = Path("characterization_results"),
    analysis_output_dir: Path = Path("analysis_output"),
    run_analysis: bool = True,
) -> dict[str, Any]:
    if perturbations is None:
        perturbations = [0.05, 0.10, 0.20]

    datasets_dir = Path(datasets_dir).resolve()
    corpora = _discover_corpora(datasets_dir)
    sens_corpus = _select_sensitivity_corpus(corpora, sensitivity_corpus)

    summary: dict[str, Any] = {
        "datasets_dir": str(datasets_dir),
        "corpora_discovered": [c.name for c in corpora],
        "sensitivity_corpus": sens_corpus.name,
        "spine_runs": [],
        "sensitivity_runs": [],
        "failures": [],
        "report_path": None,
    }

    for corpus in corpora:
        record = _run_one(
            corpus,
            perturbation=spine_perturbation,
            seed=seed,
            output_dir=output_dir,
            config_path=config_path,
            label="spine",
        )
        if record["ok"]:
            summary["spine_runs"].append(record)
        else:
            summary["failures"].append(record)

    extra_perts = [p for p in perturbations if p != spine_perturbation]
    for p in extra_perts:
        record = _run_one(
            sens_corpus,
            perturbation=p,
            seed=seed,
            output_dir=output_dir,
            config_path=config_path,
            label="sensitivity",
        )
        if record["ok"]:
            summary["sensitivity_runs"].append(record)
        else:
            summary["failures"].append(record)

    if run_analysis:
        try:
            report_path = run_analyze(
                output_dir,
                output_dir=analysis_output_dir,
                skip_figures=False,
            )
            summary["report_path"] = str(report_path)
        except Exception as e:
            summary["failures"].append(
                {"stage": "analyze", "error": str(e), "ok": False}
            )

    return summary
