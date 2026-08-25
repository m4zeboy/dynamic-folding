# ADR 0013: Name Validation via Vector Similarity

Date: 2026-05-01

## Status

Proposed.

## Context

The system proposes folder names using LLMs (Ollama) or TF-IDF. While cluster cohesion (Silhouette) measures mathematical grouping, it does not validate if the *name* itself is semantically representative of the cluster members. For a TCC research project, a quantitative metric for naming accuracy is required.

## Decision

1.  **Vector Similarity Metric:** Calculate a "Name Score" using the Cosine Similarity between:
    -   The embedding vector of the proposed folder name.
    -   The mean vector (centroid) of the cluster members' embeddings.
2.  **Pipeline Injection:** The `Proposer` will receive an `embed_text` callback from the `Pipeline` to allow on-the-fly embedding of generated names without requiring the Proposer to manage model state.
3.  **Storage:** Store results in a new `name_scores: dict[str, float]` field within the `StructureProposal` contract.
4.  **Thresholding:** In the UI, use the same color-coding logic (Green/Yellow/Red) as `cohesion_score` to signal naming confidence to the user.

## Rationale

-   **Academic Validation:** Provides an empirical way to compare naming providers (Ollama vs. TF-IDF).
-   **Hallucination Detection:** Detects if an LLM generates a creative but inaccurate name that diverges from the cluster's semantic center.
-   **Reusability:** Leverages the existing SBERT/Embedding engine already loaded in the pipeline.

## Consequences

-   Small performance overhead (one extra embedding call per cluster).
-   Requires the Proposer contract to be updated to accept an embedding function.
-   Contracts v1 is extended with an optional field.
