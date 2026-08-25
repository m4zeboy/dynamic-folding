from __future__ import annotations

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from dynamic_folding.clustering.result import AgglomerativeLinkage, ClusterPartition


def _labels_at_threshold(X: np.ndarray, threshold: float, linkage: str) -> list[int]:
    cut = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=threshold,
        linkage=linkage,
    )
    return [int(x) for x in cut.fit_predict(X).tolist()]


def _score_partition(labels: list[int], min_cluster_size: int) -> int:
    sizes: dict[int, int] = {}
    for lab in labels:
        sizes[lab] = sizes.get(lab, 0) + 1
    return sum(cnt for cnt in sizes.values() if cnt >= min_cluster_size)


def _select_threshold(
    X: np.ndarray,
    distances: np.ndarray,
    min_cluster_size: int,
    linkage: str,
) -> tuple[float, list[int]]:
    """Enumerate candidate cut thresholds and select the one that maximises:
      1. non-outlier coverage (files in clusters >= min_cluster_size)
      2. lower threshold (prefer tighter, more granular clusters on ties)
    """
    # Each candidate threshold is the midpoint between two consecutive merge
    # distances, excluding the final merge (which produces a single root cluster).
    unique_d = np.unique(distances)
    candidates: list[float] = []
    for i in range(len(unique_d) - 1):
        candidates.append(float((unique_d[i] + unique_d[i + 1]) / 2.0))

    best_score: int = -1
    best_t: float = float(unique_d[-1]) * 2  # sentinel: above all merges
    best_labels: list[int] = [0] * len(X)

    for t in candidates:
        labs = _labels_at_threshold(X, t, linkage)
        score = _score_partition(labs, min_cluster_size)
        # Maximise coverage; break ties by preferring the lower (tighter) threshold.
        if score > best_score or (score == best_score and t < best_t):
            best_score = score
            best_t = t
            best_labels = labs

    return best_t, best_labels


def cluster_agglomerative_tree(
    vectors: list[list[float]],
    *,
    min_cluster_size: int = 1,
    linkage: str = "ward",
) -> ClusterPartition:
    if not vectors:
        return ClusterPartition(labels=[], distance_threshold=0.0)
    if len(vectors) == 1:
        return ClusterPartition(labels=[0], distance_threshold=0.0)

    X = np.asarray(vectors, dtype=float)

    # Build the full tree to inspect all merge distances.
    full = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=0.0,
        linkage=linkage,
        compute_distances=True,
    )
    full.fit(X)
    distances = np.asarray(getattr(full, "distances_", []), dtype=float)

    thr, labels = _select_threshold(X, distances, min_cluster_size, linkage)

    # Mark small clusters as outliers.
    sizes: dict[int, int] = {}
    for lab in labels:
        sizes[lab] = sizes.get(lab, 0) + 1
    labels = [-1 if sizes.get(lab, 0) < min_cluster_size else lab for lab in labels]

    # Re-map non-outlier cluster ids to deterministic 0..K-1 (first-occurrence order).
    remap: dict[int, int] = {}
    next_id = 0
    out: list[int] = []
    for lab in labels:
        if lab == -1:
            out.append(-1)
            continue
        if lab not in remap:
            remap[lab] = next_id
            next_id += 1
        out.append(remap[lab])

    # Capture the full linkage tree for multi-level hierarchy extraction.
    ag_linkage = AgglomerativeLinkage(
        children=[(int(l), int(r)) for l, r in full.children_],
        distances=[float(d) for d in full.distances_],
        n_leaves=len(vectors),
    )

    return ClusterPartition(
        labels=out,
        linkage=ag_linkage,
        distance_threshold=float(thr),
    )
