# ADR 0010: Hierarchical Subdivision via Recursive Re-clustering

Date: 2026-05-01

> **Note:** The top-level outlier folder named here as `_Review` was renamed to
> `Outros` in ADR 0026 (post-Sprint-19 polish). The "keep sub-level outliers in
> the parent" rule described below is unchanged.

## Status

Accepted.

## Context

We need to support multi-level folder proposals (`max_levels > 1`) for all clustering algorithms, including `hdbscan` and `agglomerative_tree`. While some algorithms (like Agglomerative) natively provide a linkage tree, others (like K-Means or HDBSCAN) may require different approaches to subdivision. 

## Decision

1.  **Mechanism:** Use **Recursive Re-clustering** as the primary mechanism for hierarchical subdivision. 
2.  **Contract Preservation:** Maintain the existing `Clusterer` contract (`Callable[[list[list[float]], dict], list[int]]`) to ensure provider agnosticism.
3.  **Sub-level Outliers:** If a sub-clustering run identifies outliers (label `-1`), these files will be kept directly in the parent folder at that level, rather than being routed to a global or nested `_Review` folder.
4.  **Thresholding:** Sub-clustering is only attempted if the parent cluster size is `>= min_cluster_size * 2`.

## Rationale

-   **Modular Consistency:** Using the same interface for top-level and sub-level clustering prevents algorithm-specific "hacks" in the proposer logic.
-   **Simplicity:** Re-running the algorithm on a subset of vectors is semantically clean and easy to test.
-   **TCC Goal:** This allows for a fair comparison of how different algorithms perform when forced to create deeper hierarchies.

## Consequences

-   `proposer.py` will become more recursive or iterative in its handling of clusters.
-   Performance for very large datasets (not yet in scope) might be affected by multiple clustering runs.
-   The `cohesion_score` (Silhouette) for subfolders will need to be calculated relative to their specific sub-partition.
