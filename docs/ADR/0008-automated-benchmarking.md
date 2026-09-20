# ADR 0008: Automated Benchmarking and Grid Search Evaluation

Date: 2026-04-30

## Status

Accepted.

## Context

To scientifically validate the "intelligence" of the tool for a TCC, it is not enough to show one result. We must demonstrate that we have evaluated multiple algorithmic configurations (Centroid-based, Hierarchical, Density-based) and embedding strategies to find the one that maximizes semantic cohesion for a specific dataset.

## Decision

1.  **Implement `benchmark` command:** Add a new command to the CLI that performs a grid search over configuration space.
2.  **Grid Dimensions:**
    - **Algorithms:** KMeans, Agglomerative Tree, HDBSCAN.
    - **Embeddings:** Fake (baseline), SBERT (semantic).
    - **Hyperparameters:** `min_cluster_size` (varying from 2 to 6).
3.  **Result Persistence:** Save results to `benchmark_results/` in a structured JSON format. This ensures that the data is durable and can be used for offline analysis and visualization in the thesis.
4.  **Ranking Logic:** Rank configurations based on the `cohesion_score` (Silhouette Score).
5.  **Telemetry:** Record metadata for each run, including:
    - Cluster count.
    - Outlier count.
    - Wall-clock time.
    - Success/Failure status.

## Rationale

-   **Empirical Evidence:** Provides a clear table of results to include in a TCC.
-   **Automation:** Manual testing of every combination is error-prone and time-consuming.
-   **Sensitivity Analysis:** Allows the researcher to see how sensitive the results are to changes in `min_cluster_size` or embedding engine.
-   **Future Proofing:** New algorithms added to the registry will be easy to include in the benchmark loop.

## Consequences

-   A new top-level folder `benchmark_results/` will be created (and should be added to `.gitignore` but tracked for the user's local research).
-   The CLI complexity increases slightly to support a new subcommand.
-   Running a full benchmark might take several minutes depending on the dataset size and hardware (due to SBERT inference).

## Note (2026-05-07)

This ADR establishes the benchmark mechanism. ADR 0018 reframes how its outputs are interpreted in the TCC: cohesion scores are evidence of *sensitivity to configuration*, not of *correctness*. The implementation described here is unchanged; only the narrative around its results is refined. This ADR is not superseded.
