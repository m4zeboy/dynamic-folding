from __future__ import annotations

import numpy as np

def reduce_umap(vectors: list[list[float]], cfg: dict) -> list[list[float]]:
    if not vectors:
        return []
    
    try:
        import umap
    except ImportError:
        # Graceful degradation: log warning (if we had a logger here) and fallback to identity
        # In this architecture, we prefer to let the validator catch this, but 
        # as a runtime fallback we return original vectors.
        return vectors
        
    n_components = int(cfg.get("n_components", 10))
    random_state = int(cfg.get("random_state", 0))
    n_neighbors = int(cfg.get("n_neighbors", 15))
    min_dist = float(cfg.get("min_dist", 0.1))
    
    X = np.asarray(vectors, dtype=float)
    n_samples, _ = X.shape
    
    # UMAP constraints: n_neighbors < n_samples
    effective_neighbors = min(n_neighbors, max(2, n_samples - 1))
    
    # If we have too few samples, UMAP might struggle or raise errors
    if n_samples < 2:
        return vectors

    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=effective_neighbors,
        min_dist=min_dist,
        random_state=random_state,
        n_jobs=1, # Better for determinism in some environments
    )
    
    reduced = reducer.fit_transform(X)
    return [x.tolist() for x in reduced]
