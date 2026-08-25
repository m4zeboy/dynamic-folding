# ADR 0006: Clustering Validation and HDBSCAN Integration

Date: 2026-04-30

## Status

Accepted.

## Context

For the TCC (Final Project), we need to move beyond heuristic-only clustering and provide mathematical validation for the proposed structures. This requires comparing different clustering paradigms (Hierarchical vs. Density-based) and calculating internal validation metrics like the Silhouette Score.

## Decision

1.  **Add HDBSCAN:** Implement HDBSCAN using `sklearn.cluster.HDBSCAN`. This provides a density-based alternative to the existing Agglomerative (Hierarchical) and KMeans (Centroid-based) algorithms.
2.  **Silhouette Score:** Calculate the Silhouette Score for every proposal. This metric measures how similar an object is to its own cluster compared to other clusters.
3.  **Contract Update:** Extend `StructureProposal` with a `cohesion_score: float` field. This allows UIs and automated tests to evaluate the quality of a proposal without re-running the ML logic.
4.  **Integration Point:** Calculate metrics within the `Proposer` stage. The proposer has access to both the raw embeddings and the generated labels, making it the most efficient place to perform evaluation before finalizing the DTO.

## Rationale

-   **Academic Rigor:** Silhouette scores provide a "Confidence Level" that is essential for a technical thesis.
-   **Paradigm Variety:** HDBSCAN is excellent at identifying "noise" and handling clusters of varying shapes/densities, offering a strong contrast to `agglomerative_tree`.
-   **Zero Dependency Growth:** By using `sklearn.cluster.HDBSCAN` (available since sklearn 1.3), we fulfill the requirement for a "simple, robust, and provider-agnostic" system without adding new libraries.

## Consequences

-   The JSON output will now include a `cohesion_score`.
-   Golden tests will need to be updated to include this new field.
-   The system can now be used to empirically test which algorithm (KMeans, Agglomerative, HDBSCAN) produces the highest cohesion for a given dataset.
