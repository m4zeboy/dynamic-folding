"""Measure the DBCV (Density-Based Clustering Validation) of the proposed grouping.

The SECOND lens, with the OPPOSITE bias to silhouette. DBCV rewards dense, connected
clusters of arbitrary shape (a long filament counts as much as a round ball), so it
is biased TOWARD density methods like HDBSCAN — exactly opposite to silhouette's
convex bias. The two lenses together (each bias declared) are the honest reading;
neither alone crowns a winner. See docs/learning/06-dbcv-metric.md and ADR 0039.

Scope decisions (ADR 0039):
- We score the REDUCED vectors the clusterer actually used (``result.reduced_vectors``,
  the ~10-dim UMAP space), NOT the 384-dim embeddings. DBCV needs density, and density
  estimation degenerates when n << d (54 files in 384-dim overflows to ~0). This means
  DBCV reads a DIFFERENT space than silhouette (the clustering workspace, which favours
  density methods), so the two are independent lenses, not a controlled head-to-head.
- The "Outros" outlier bucket is fed to DBCV as noise (label -1), exactly as the
  algorithm produced it, and counted. Excluding it would inflate the score; DBCV is
  designed to account for noise. (Note: DBCV_without_noise == DBCV / coverage, so we
  never report a separate "without noise" number — coverage already carries it.)
- Top-level folders only; a nested file counts under its top-level parent.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from hdbscan.validity import validity_index

from dynamic_folding.contracts.run_result import RunResult
from dynamic_folding.evaluation.silhouette import _top_level_labels

# Label fed to DBCV for files in the "Outros" bucket (DBCV's noise convention).
_NOISE = -1


@dataclass(frozen=True)
class GroupDBCV:
    name: str  # the folder's display name
    score: float  # per-cluster validity index in [-1, 1]
    n_files: int  # files in this top-level group

    def to_dict(self) -> dict:
        return {"name": self.name, "score": self.score, "n_files": self.n_files}


@dataclass(frozen=True)
class DBCVResult:
    score: float | None  # None when undefined (see `reason`)
    n_groups: int  # top-level groups scored (excludes Outros)
    n_files_scored: int  # files assigned to a scored group
    n_outliers: int  # files in the Outros bucket (fed as noise, counted)
    reason: str | None = None  # why score is None, when it is
    per_group: list[GroupDBCV] = field(default_factory=list)  # empty when score is None

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "n_groups": self.n_groups,
            "n_files_scored": self.n_files_scored,
            "n_outliers": self.n_outliers,
            "reason": self.reason,
            "per_group": [g.to_dict() for g in self.per_group],
        }


def _vectors_and_labels(
    result: RunResult,
) -> tuple[list[list[float]], list[int], int, list[str]]:
    """The reduced (vector, top-level label) pairs, the outlier count, and the
    ordered group names.

    Reads ``result.reduced_vectors`` (the space the clustering ran in), aligned by
    index with ``result.embeddings``. Outliers ("Outros") get label -1: fed to DBCV
    as noise and counted, exactly as the algorithm produced them.
    """
    label_of, group_names = _top_level_labels(result.proposal)

    vectors: list[list[float]] = []
    labels: list[int] = []
    n_outliers = 0
    for e, rvec in zip(result.embeddings, result.reduced_vectors):
        lab = label_of.get(e.file.rel_path, _NOISE)
        vectors.append(list(rvec))
        labels.append(lab)
        if lab == _NOISE:
            n_outliers += 1
    return vectors, labels, n_outliers, group_names


def dbcv_of_run(result: RunResult) -> DBCVResult:
    """DBCV of the run's top-level grouping, scored on the reduced vectors."""
    reduced = result.reduced_vectors
    if not reduced or len(reduced) != len(result.embeddings):
        # No reduced vectors to score (identity reducer, or a run predating the
        # reduced_vectors contract field). DBCV needs the clustering's own space.
        return DBCVResult(
            score=None,
            n_groups=0,
            n_files_scored=0,
            n_outliers=0,
            reason="vetores reduzidos indisponíveis (redutor identity ou execução anterior ao contrato v2)",
        )

    vectors, labels, n_outliers, group_names = _vectors_and_labels(result)
    scored = [lab for lab in labels if lab != _NOISE]
    n_groups = len(set(scored))
    n_files_scored = len(scored)
    if n_groups < 2 or n_files_scored < 2:
        return DBCVResult(
            score=None,
            n_groups=n_groups,
            n_files_scored=n_files_scored,
            n_outliers=n_outliers,
            reason="é preciso ao menos 2 grupos com 2 ou mais arquivos",
        )

    X = np.asarray(vectors, dtype=np.float64)
    y = np.asarray(labels, dtype=np.intp)
    try:
        # Degenerate partitions make the density math divide-by-zero / overflow;
        # we handle the resulting non-finite score explicitly below, so silence
        # the numpy warnings rather than letting them leak into output.
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            overall, per_cluster = validity_index(X, y, per_cluster_scores=True)
        overall = float(overall)
    except Exception:  # a degenerate partition must not abort the harness
        # Typically a group too small for the density math (its cluster MST has no
        # internal edges) — e.g. k-means forced into many tiny groups at high k.
        return DBCVResult(
            score=None,
            n_groups=n_groups,
            n_files_scored=n_files_scored,
            n_outliers=n_outliers,
            reason="grupo pequeno demais para o DBCV",
        )

    if not np.isfinite(overall):
        return DBCVResult(
            score=None,
            n_groups=n_groups,
            n_files_scored=n_files_scored,
            n_outliers=n_outliers,
            reason="partição degenerada (resultado não-finito)",
        )

    per_group = [
        GroupDBCV(
            name=group_names[g],
            score=(float(per_cluster[g]) if g < len(per_cluster)
                   and np.isfinite(per_cluster[g]) else 0.0),
            n_files=int((y == g).sum()),
        )
        for g in sorted(set(scored))
    ]

    return DBCVResult(
        score=overall,
        n_groups=n_groups,
        n_files_scored=n_files_scored,
        n_outliers=n_outliers,
        per_group=per_group,
    )
