from __future__ import annotations

import numpy as np

from dynamic_folding.clustering.result import ClusterPartition


def cluster_random(
    vectors: list[list[float]], *, k: int, random_state: int
) -> ClusterPartition:
    if not vectors:
        return ClusterPartition(labels=[])
    if k <= 1:
        return ClusterPartition(labels=[0 for _ in vectors])

    rng = np.random.default_rng(random_state)
    labels = rng.integers(0, k, size=len(vectors))
    return ClusterPartition(labels=[int(x) for x in labels.tolist()])
