"""Measure the Silhouette score of the tool's proposed top-level grouping.

One metric, kept small and self-contained on purpose. Silhouette is a number in
[-1, +1]: higher means each group is tight inside and well separated from the
other groups; ~0 means groups overlap; negative means files look misgrouped.

Scope decisions (see the plan):
- We score the TOP-LEVEL folders only. A file inside a subfolder counts under its
  top-level parent (the hierarchy is flattened up).
- The "Outros" outlier bucket is not a real group, so its files are skipped (we
  report how many were skipped, so the score can't silently flatter itself).
- We score the raw embeddings the run produced (the honest semantic space), not
  the UMAP-reduced vectors the clusterer used.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.metrics import silhouette_samples, silhouette_score

from dynamic_folding.contracts.proposal import FolderNode, StructureProposal
from dynamic_folding.contracts.run_result import RunResult

# The proposer tags the outlier bucket with this display name; it is not a group.
_OUTLIER_DISPLAY_NAME = "Outros"


@dataclass(frozen=True)
class GroupSilhouette:
    name: str  # the folder's display name
    score: float  # mean silhouette of the files in this top-level group
    n_files: int  # files in this group

    def to_dict(self) -> dict:
        return {"name": self.name, "score": self.score, "n_files": self.n_files}


@dataclass(frozen=True)
class SilhouetteResult:
    score: float | None  # None when the score is undefined (see `reason`)
    n_groups: int  # top-level groups scored (excludes Outros)
    n_files_scored: int  # files assigned to a scored group
    n_outliers: int  # files in the Outros bucket (skipped)
    reason: str | None = None  # why score is None, when it is
    per_group: list[GroupSilhouette] = field(default_factory=list)  # empty when score is None

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "n_groups": self.n_groups,
            "n_files_scored": self.n_files_scored,
            "n_outliers": self.n_outliers,
            "reason": self.reason,
            "per_group": [g.to_dict() for g in self.per_group],
        }


def _all_files(folder: FolderNode) -> list[str]:
    """Every file under a folder: its own files plus all nested subfolders."""
    rels = list(folder.files)
    for sub in folder.subfolders:
        rels.extend(_all_files(sub))
    return rels


def _top_level_labels(
    proposal: StructureProposal,
) -> tuple[dict[str, int], list[str]]:
    """Map each file's rel_path -> top-level group index (skipping Outros).

    Also return the group display names ordered by group index, so a per-group
    readout can name each folder.
    """
    label_of: dict[str, int] = {}
    group_names: list[str] = []
    for folder in proposal.folders:
        if folder.display_name == _OUTLIER_DISPLAY_NAME:
            continue
        group_idx = len(group_names)
        for rel in _all_files(folder):
            label_of[rel] = group_idx
        group_names.append(folder.display_name or folder.name)
    return label_of, group_names


def _vectors_and_labels(
    result: RunResult,
) -> tuple[list[list[float]], list[int], int, list[str]]:
    """The scored (vector, top-level label) pairs, the outlier count, and the
    ordered group names.

    Outliers (the "Outros" bucket) carry no label: they are counted, not scored.
    Both the real silhouette and its random baseline read through this one helper,
    so they see exactly the same files in exactly the same raw-embedding space.
    """
    label_of, group_names = _top_level_labels(result.proposal)

    vectors: list[list[float]] = []
    labels: list[int] = []
    n_outliers = 0
    for e in result.embeddings:
        lab = label_of.get(e.file.rel_path)
        if lab is None:
            n_outliers += 1
        else:
            vectors.append(list(e.vector))
            labels.append(lab)
    return vectors, labels, n_outliers, group_names


def silhouette_of_run(result: RunResult) -> SilhouetteResult:
    """Silhouette of the run's top-level grouping, scored on the raw embeddings."""
    vectors, labels, n_outliers, group_names = _vectors_and_labels(result)

    n_groups = len(set(labels))
    if n_groups < 2 or len(vectors) < 2:
        return SilhouetteResult(
            score=None,
            n_groups=n_groups,
            n_files_scored=len(labels),
            n_outliers=n_outliers,
            reason="need at least 2 groups with 2+ files for a silhouette score",
        )

    try:
        samples = silhouette_samples(vectors, labels)
    except Exception as exc:  # e.g. every file in its own group
        return SilhouetteResult(
            score=None,
            n_groups=n_groups,
            n_files_scored=len(labels),
            n_outliers=n_outliers,
            reason=f"silhouette undefined: {exc}",
        )

    # The overall score is the mean of the per-file samples (identical to
    # silhouette_score); per-group scores are the mean within each group.
    labels_arr = np.asarray(labels)
    per_group = [
        GroupSilhouette(
            name=group_names[g],
            score=float(samples[labels_arr == g].mean()),
            n_files=int((labels_arr == g).sum()),
        )
        for g in sorted(set(labels))
    ]

    return SilhouetteResult(
        score=float(samples.mean()),
        n_groups=n_groups,
        n_files_scored=len(labels),
        n_outliers=n_outliers,
        per_group=per_group,
    )


# How many random shufflings to average into the "random floor". Cheap at this
# corpus size; more shuffles only steady the floor, they don't move it.
_DEFAULT_PERMUTATIONS = 1000


@dataclass(frozen=True)
class SilhouetteBaselineResult:
    real: SilhouetteResult  # the actual silhouette of the proposed grouping
    baseline_mean: float | None  # mean silhouette of random same-size groupings
    baseline_std: float | None  # spread of those random scores (give-or-take)
    gap: float | None  # real.score - baseline_mean (how far above chance)
    n_permutations: int  # how many random shufflings were averaged
    reason: str | None = None  # why the baseline is undefined, when it is

    def to_dict(self) -> dict:
        return {
            "real": self.real.to_dict(),
            "baseline_mean": self.baseline_mean,
            "baseline_std": self.baseline_std,
            "gap": self.gap,
            "n_permutations": self.n_permutations,
            "reason": self.reason,
        }


def silhouette_baseline_of_run(
    result: RunResult,
    *,
    n_permutations: int = _DEFAULT_PERMUTATIONS,
    random_state: int = 0,
) -> SilhouetteBaselineResult:
    """Calibrate the silhouette against a random "floor".

    Keep the exact same files and the exact same group sizes, but shuffle which
    file lands in which group, recompute the silhouette, and repeat. The mean of
    those shuffles is roughly the score you'd get by chance; the real silhouette
    is meaningful only insofar as it sits above that floor. Deterministic: the
    same input + seed gives the same floor. See docs/learning/05-silhouette-metric.md.
    """
    real = silhouette_of_run(result)
    if real.score is None:
        # No defined silhouette to calibrate -> no baseline.
        return SilhouetteBaselineResult(
            real=real,
            baseline_mean=None,
            baseline_std=None,
            gap=None,
            n_permutations=0,
            reason=real.reason,
        )

    vectors, labels, _, _ = _vectors_and_labels(result)
    rng = np.random.default_rng(random_state)
    # rng.permutation returns a shuffled copy, so `labels` is preserved each round
    # and only group *membership* changes (the group sizes stay fixed).
    scores = [
        float(silhouette_score(vectors, rng.permutation(labels)))
        for _ in range(n_permutations)
    ]

    baseline_mean = float(np.mean(scores))
    baseline_std = float(np.std(scores))
    return SilhouetteBaselineResult(
        real=real,
        baseline_mean=baseline_mean,
        baseline_std=baseline_std,
        gap=real.score - baseline_mean,
        n_permutations=n_permutations,
    )
