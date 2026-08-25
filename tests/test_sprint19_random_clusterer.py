"""Sprint 19: random clusterer floor baseline.

These tests exist to be failing first per AGENTS.md DoD. They lock in the
behavioral contract before implementation. See ADR 0018 and SPEC Sprint 19.
"""
from __future__ import annotations

import pytest


def test_random_clusterer_registered() -> None:
    from dynamic_folding.core.registries import CLUSTERERS

    assert "random" in CLUSTERERS.keys(), (
        "Sprint 19 requires 'random' as a registered clusterer for the floor "
        "baseline. See ADR 0018."
    )


def test_random_clusterer_module_exists() -> None:
    try:
        from dynamic_folding.clustering.random_baseline import cluster_random  # noqa: F401
    except ImportError:
        pytest.fail("dynamic_folding.clustering.random_baseline.cluster_random must exist")


def test_random_clusterer_deterministic() -> None:
    from dynamic_folding.clustering.random_baseline import cluster_random

    vectors = [[float(i), float(i % 3)] for i in range(20)]
    r1 = cluster_random(vectors, k=4, random_state=42)
    r2 = cluster_random(vectors, k=4, random_state=42)
    assert r1.labels == r2.labels


def test_random_clusterer_different_seeds_differ() -> None:
    from dynamic_folding.clustering.random_baseline import cluster_random

    vectors = [[float(i)] for i in range(50)]
    r1 = cluster_random(vectors, k=5, random_state=1)
    r2 = cluster_random(vectors, k=5, random_state=2)
    assert r1.labels != r2.labels, "Different seeds must (almost surely) yield different labels"


def test_random_clusterer_respects_k() -> None:
    from dynamic_folding.clustering.random_baseline import cluster_random

    vectors = [[float(i)] for i in range(30)]
    k = 4
    result = cluster_random(vectors, k=k, random_state=0)
    assert len(result.labels) == len(vectors)
    assert all(0 <= label < k for label in result.labels)


def test_random_clusterer_handles_empty() -> None:
    from dynamic_folding.clustering.random_baseline import cluster_random

    result = cluster_random([], k=3, random_state=0)
    assert result.labels == []


def test_random_clusterer_k_floor() -> None:
    """k <= 1 collapses to a single cluster, mirroring kmeans behavior."""
    from dynamic_folding.clustering.random_baseline import cluster_random

    vectors = [[float(i)] for i in range(10)]
    result = cluster_random(vectors, k=1, random_state=0)
    assert all(label == 0 for label in result.labels)


def test_random_clusterer_silhouette_near_zero() -> None:
    """Random labels on obvious 2-cluster data must NOT score high silhouette."""
    import numpy as np
    from sklearn.metrics import silhouette_score

    from dynamic_folding.clustering.random_baseline import cluster_random

    rng = np.random.default_rng(seed=0)
    cluster_a = rng.normal(loc=[0.0, 0.0], scale=0.1, size=(30, 2))
    cluster_b = rng.normal(loc=[5.0, 5.0], scale=0.1, size=(30, 2))
    vectors = np.concatenate([cluster_a, cluster_b]).tolist()

    result = cluster_random(vectors, k=2, random_state=42)
    score = silhouette_score(vectors, result.labels)

    assert abs(score) < 0.15, (
        f"Random clusterer produced silhouette {score:.3f}; expected ~0. "
        "Either the implementation is not actually random, or the tolerance "
        "is too tight for the fixture size."
    )
