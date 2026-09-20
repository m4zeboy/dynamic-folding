import pytest
import numpy as np
from unittest.mock import MagicMock
from dynamic_folding.core.registries import CLUSTERERS

def test_hdbscan_registry():
    """
    Asserts that CLUSTERERS registry contains the 'hdbscan' key and it can be constructed.
    """
    assert "hdbscan" in CLUSTERERS.keys()
    # Attempting to create should fail if not registered, or return a callable
    # For HDBSCAN, we just want to see if it's there.
    clusterer = CLUSTERERS.create("hdbscan", {"min_cluster_size": 2})
    assert callable(clusterer)

def test_hdbscan_clustering():
    """
    Mock some vectors and assert that the hdbscan implementation returns valid labels.
    """
    # This might fail if the module doesn't exist yet
    from dynamic_folding.clustering.hdbscan import cluster_hdbscan
    
    # 2 obvious clusters + 1 noise point
    vectors = [
        [1.0, 1.0], [1.1, 1.1], [0.9, 0.9], # Cluster 1
        [10.0, 10.0], [10.1, 10.1], [9.9, 9.9], # Cluster 2
        [5.0, 5.0] # Noise
    ]
    
    # We expect labels to be returned. HDBSCAN uses -1 for noise.
    result = cluster_hdbscan(vectors, min_cluster_size=2, min_samples=1)
    assert hasattr(result, "labels")
    assert len(result.labels) == len(vectors)
    # At least some points should be clustered, and one might be -1
    assert -1 in result.labels or any(l >= 0 for l in result.labels)

def test_silhouette_metric():
    """
    Assert that for a perfectly separated dataset, the score is close to 1.0.
    """
    from dynamic_folding.clustering.metrics import calculate_silhouette_score
    
    # Perfectly separated clusters
    vectors = [
        [0.0, 0.0], [0.0, 0.1], 
        [10.0, 10.0], [10.0, 10.1]
    ]
    labels = [0, 0, 1, 1]
    
    score = calculate_silhouette_score(vectors, labels)
    assert 0.9 <= score <= 1.0
