from __future__ import annotations

from pathlib import Path
import pytest
from dynamic_folding.core.pipeline import run_pipeline
from dynamic_folding.core.registries import REDUCERS

def test_reducer_registry():
    assert "identity" in REDUCERS.keys()
    assert "pca" in REDUCERS.keys()

def test_pca_reducer_logic():
    from dynamic_folding.reducer.pca import reduce_pca
    # 4 samples, 5 features
    vectors = [
        [1.0, 2.0, 3.0, 4.0, 5.0],
        [1.1, 2.1, 3.1, 4.1, 5.1],
        [10.0, 20.0, 30.0, 40.0, 50.0],
        [10.1, 20.1, 30.1, 40.1, 50.1],
    ]
    cfg = {"n_components": 2}
    reduced = reduce_pca(vectors, cfg)
    
    assert len(reduced) == 4
    assert len(reduced[0]) == 2

def test_pca_reducer_fallback():
    from dynamic_folding.reducer.pca import reduce_pca
    vectors = [[1.0, 2.0]]
    cfg = {"n_components": 10} # More than samples/features
    reduced = reduce_pca(vectors, cfg)
    
    assert len(reduced) == 1
    assert len(reduced[0]) == 1 # PCA(n_components=1) because n_samples=1

def test_pipeline_with_pca(tmp_path):
    # Smoke test: run pipeline with PCA enabled
    (tmp_path / "a.txt").write_text("content a")
    (tmp_path / "b.txt").write_text("content b")
    (tmp_path / "c.txt").write_text("content c")
    (tmp_path / "d.txt").write_text("content d")
    (tmp_path / "e.txt").write_text("content e")

    overrides = {
        "reducer": {
            "provider": "pca",
            "n_components": 2
        },
        "embedding": {
            "provider": "fake",
            "fake_dim": 8
        }
    }
    
    result = run_pipeline(tmp_path, overrides=overrides)
    assert result.proposal is not None
    # Confirm it ran through the full pipeline (the pipeline stamps a scan note).
    assert any("Scanned" in n for n in result.proposal.notes)

def test_umap_reducer_logic():
    # Only run if umap is installed
    try:
        import umap
    except ImportError:
        pytest.skip("umap-learn not installed")
        
    from dynamic_folding.reducer.umap import reduce_umap
    # Need enough samples for UMAP to work well
    vectors = [[float(i), float(j)] for i in range(10) for j in range(2)]
    cfg = {"n_components": 1, "n_neighbors": 5}
    reduced = reduce_umap(vectors, cfg)
    
    assert len(reduced) == 20
    assert len(reduced[0]) == 1
