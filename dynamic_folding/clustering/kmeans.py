from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans

from dynamic_folding.clustering.result import ClusterPartition


def cluster_kmeans(vectors: list[list[float]], *, k: int, random_state: int) -> ClusterPartition:
    if not vectors:
        return ClusterPartition(labels=[])
    if k <= 1:
        return ClusterPartition(labels=[0 for _ in vectors])
    k = min(k, len(vectors))

    X = np.asarray(vectors, dtype=float)
    km = KMeans(n_clusters=k, n_init="auto", random_state=random_state)
    labels = km.fit_predict(X)
    return ClusterPartition(labels=[int(x) for x in labels.tolist()])
