# ADR 0009: Dimensionality Reduction Stage (Reducer)

Date: 2026-04-30

## Status

Proposed.

## Context

As the project matures towards a research platform (TCC), we need to handle high-dimensional embeddings more effectively. Algorithms like HDBSCAN suffer from the "curse of dimensionality," where distance metrics become less meaningful in high-dimensional spaces (e.g., 384D from SBERT). Reducing dimensionality before clustering can significantly improve cluster density and quality.

## Decision

1.  **New Pipeline Stage:** Introduce a `Reducer` stage between `Embedding` and `Clustering`.
2.  **Registry:** Add `REDUCERS` to `dynamic_folding/core/registries.py`.
3.  **Initial Implementations:**
    *   `identity`: A no-op reducer (default) to maintain backward compatibility.
    *   `pca`: A linear reduction using `sklearn.decomposition.PCA`.
4.  **Future-proofing:** Design the interface to support `UMAP` as an optional dependency in later sprints.
5.  **Configuration:** Add a `[reducer]` section to the configuration TOML.
    *   `reducer.provider`: "identity", "pca", or "umap".
    *   `reducer.n_components`: Target number of dimensions (default: 10).

## Rationale

-   **Modular Design:** Adding a dedicated stage follows the existing architectural pattern.
-   **Improved Clustering:** PCA/UMAP can condense semantic information, making clusters "tighter" for density-based algorithms.
-   **Baseline Safety:** PCA is available in `scikit-learn`, requiring no new dependencies. UMAP can be added as an optional extra.

## Consequences

-   The pipeline execution flow becomes: `Scanner -> Extractor -> Preprocess -> Embedding -> Reducer -> Clustering -> Namer -> Proposer`.
-   Configuration files will need a new `[reducer]` block to control this behavior.
-   The `cohesion_score` (Silhouette) will still be calculated on the **original** high-dimensional embeddings to ensure the validation reflects the true semantic similarity, not just the artifacts of the reduction.
