# ADR 0004: Hierarchical Clustering via scikit-learn Agglomerative Tree + Outliers

Date: 2026-04-30

> **Note:** The `proposal.outliers_folder` default named here as `_Review` was
> renamed to `Outros` in ADR 0026 (post-Sprint-19 polish). The routing
> mechanism described in this ADR is unchanged.

## Decision

1. Implement the first hierarchy-producing clustering option using scikit-learn agglomerative clustering, exposed as `clustering.algorithm = "agglomerative_tree"`.
2. Automatically derive the number of clusters (`K`) by cutting the agglomerative merge tree (dendrogram) via either:
   - a user-provided `clustering.distance_threshold`, or
   - an `auto` cut heuristic derived from merge distances and `clustering.min_cluster_size`.
3. Handle outliers by routing members of clusters smaller than `clustering.min_cluster_size` to a dedicated folder `proposal.outliers_folder` (default `_Review` — renamed to `Outros` in ADR 0026).

## Status

Accepted.

## Rationale

- We need organic grouping and hierarchy from similarity data without adding new dependencies.
- scikit-learn is already allowed; agglomerative clustering is deterministic and supports hierarchical structure.
- A tree allows us to propose multiple folder levels (`proposal.max_levels`) without re-running a flat algorithm at each level as a hack.
- Minimum cluster size is a simple, stable mechanism to avoid noisy micro-folders and provides a clear outlier definition for review.

## Related

- ADR 0005: details the scoring rule used for the `auto` cut strategy, including why the
  "fewer non-outlier clusters" secondary criterion from the initial SPEC was not implemented.

## Consequences

- Clustering output must include enough information to build and cut a tree (merge distances and structure) or an equivalent representation.
- The proposer must treat clustering as an injected strategy from the registry, and must build hierarchy from the clusterer's hierarchical output.
- Default behavior will favor stability and non-trivial clusters; small groups are collected under `_Review` rather than forced into folders.
- We are explicitly deferring density-based clustering (HDBSCAN) until we have a need that justifies the extra dependency.
