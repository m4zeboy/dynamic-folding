"""CSV export for the evaluation metrics (Silhouette, DBCV, external agreement).

Plain-text export so someone without this repo's HTML report (e.g. an advisor
running the tool on their own dataset) can open the numbers in a spreadsheet.
No precedent for CSV in this project — this module is the first, kept small
and dependency-free (stdlib ``csv`` only).
"""
from __future__ import annotations

import csv
from pathlib import Path

from dynamic_folding.evaluation.comparison import ComparisonResult
from dynamic_folding.evaluation.external import ExternalEvaluationResult
from dynamic_folding.evaluation.silhouette import SilhouetteBaselineResult

_COMPARISON_FIELDS = (
    "algorithm",
    "score",
    "baseline_mean",
    "baseline_std",
    "gap",
    "dbcv_score",
    "dbcv_reason",
    "n_groups",
    "n_files_scored",
    "n_outliers",
    "n_total",
    "reason",
)


def write_comparison_csv(res: ComparisonResult, path: str | Path) -> None:
    """One row per algorithm (the structural + silhouette + DBCV descriptors).

    ``group_sizes`` and ``effective_config`` are nested/variable-shaped and are
    left out of the flat table; they remain available via ``--json``.
    """
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_COMPARISON_FIELDS)
        writer.writeheader()
        for algo in res.algorithms:
            row = algo.to_dict()
            writer.writerow({k: row[k] for k in _COMPARISON_FIELDS})


_SILHOUETTE_GROUP_FIELDS = ("name", "score", "n_files")


def write_silhouette_csv(res: SilhouetteBaselineResult, path: str | Path) -> None:
    """Per-group rows, then a differently-shaped summary block.

    The overall score/baseline/gap don't fit the per-group
    ``name, score, n_files`` columns, so they're written as a second
    ``metric, value`` block below a blank line instead of forcing one shape.
    """
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_SILHOUETTE_GROUP_FIELDS)
        writer.writeheader()
        for group in res.real.per_group:
            writer.writerow(group.to_dict())

        f.write("\n")
        summary = csv.writer(f)
        summary.writerow(["metric", "value"])
        summary.writerow(["score", res.real.score])
        summary.writerow(["n_groups", res.real.n_groups])
        summary.writerow(["n_files_scored", res.real.n_files_scored])
        summary.writerow(["n_outliers", res.real.n_outliers])
        summary.writerow(["baseline_mean", res.baseline_mean])
        summary.writerow(["baseline_std", res.baseline_std])
        summary.writerow(["gap", res.gap])
        summary.writerow(["n_permutations", res.n_permutations])
        summary.writerow(["reason", res.reason])


_EXTERNAL_FIELDS = (
    "ari",
    "nmi",
    "ami",
    "n_files",
    "n_reference_classes",
    "n_predicted_groups",
    "n_predicted_outros",
    "average_method",
)


def write_external_evaluation_csv(
    res: ExternalEvaluationResult, path: str | Path
) -> None:
    """Write the one-row, corpus-level external-evaluation summary.

    The class distributions are JSON-only because their column set changes with
    the corpus; the flat CSV remains suitable for a three-corpus table.
    """
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_EXTERNAL_FIELDS)
        writer.writeheader()
        row = res.to_dict()
        writer.writerow({field: row[field] for field in _EXTERNAL_FIELDS})
