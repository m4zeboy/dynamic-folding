from __future__ import annotations

from collections import defaultdict

import numpy as np
from sklearn.metrics import silhouette_score


def calculate_silhouette_score(vectors: list[list[float]], labels: list[int]) -> float:
    """
    Calculate the Silhouette Score for the given clustering.
    Handles edge cases: if only 1 cluster is found or all points are noise (-1), returns 0.0.
    """
    if not vectors or not labels or len(vectors) != len(labels):
        return 0.0

    unique_labels = set(labels)
    # Remove noise label if present for counting valid clusters
    non_noise_labels = {lbl for lbl in unique_labels if lbl != -1}

    # Silhouette score requires at least 2 clusters and more than 1 point.
    # If we have only 1 cluster or 0 clusters (all noise), return 0.0.
    if len(non_noise_labels) < 2:
        return 0.0

    # sklearn.metrics.silhouette_score handles -1 as just another cluster label,
    # but typically it's better to treat it as noise. 
    # However, for consistency with TCC requirements, we use the raw labels provided.
    # Most HDBSCAN/KMeans users will want to know how cohesive the non-noise parts are,
    # but standard silhouette_score will include -1 if it's in labels.
    
    try:
        X = np.asarray(vectors, dtype=float)
        score = silhouette_score(X, labels)
        return float(score)
    except Exception:
        # e.g. if all samples belong to one cluster or something else goes wrong
        return 0.0


def calculate_per_cluster_silhouette(vectors: list[list[float]], labels: list[int]) -> dict[int, float]:
    """
    Calculate the average Silhouette Score for each cluster.
    Returns a mapping of label -> average score.
    Noise (-1) is assigned a score of 0.0.
    """
    if not vectors or not labels or len(vectors) != len(labels):
        return {}

    unique_labels = {lbl for lbl in labels if lbl != -1}
    if len(unique_labels) < 2:
        # Cannot calculate silhouette with < 2 clusters.
        return {lbl: 0.0 for lbl in set(labels)}

    from sklearn.metrics import silhouette_samples

    try:
        X = np.asarray(vectors, dtype=float)
        sample_scores = silhouette_samples(X, labels)
        
        cluster_scores: dict[int, list[float]] = defaultdict(list)
        for i, lbl in enumerate(labels):
            cluster_scores[lbl].append(float(sample_scores[i]))
            
        return {lbl: float(np.mean(scores)) for lbl, scores in cluster_scores.items()}
    except Exception:
        return {lbl: 0.0 for lbl in set(labels)}
