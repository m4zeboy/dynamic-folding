from __future__ import annotations

import numpy as np
from sklearn.decomposition import PCA

def reduce_pca(vectors: list[list[float]], cfg: dict) -> list[list[float]]:
    if not vectors:
        return []
    
    n_components = int(cfg.get("n_components", 10))
    random_state = int(cfg.get("random_state", 0))
    
    X = np.asarray(vectors, dtype=float)
    n_samples, n_features = X.shape
    
    # PCA constraints: n_components <= min(n_samples, n_features)
    effective_n = min(n_components, n_samples, n_features)
    
    if effective_n < 1:
        # Fallback if we have too few samples/features for the requested reduction
        return vectors
        
    pca = PCA(n_components=effective_n, random_state=random_state)
    reduced = pca.fit_transform(X)
    
    return [x.tolist() for x in reduced]
