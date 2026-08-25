# ADR 0005: Auto-Cut Scoring Rule for Agglomerative Tree Clustering

Date: 2026-04-30

## Decision

When `clustering.cut_strategy = "auto"` (the default), the threshold for cutting the
agglomerative merge tree is selected by enumerating every candidate threshold (one midpoint
between each pair of consecutive, distinct merge distances) and scoring each resulting flat
partition by:

1. **Primary — maximize non-outlier coverage**: count of files that fall into clusters
   whose size is ≥ `clustering.min_cluster_size`. Higher is better.
2. **Tertiary — prefer lower threshold**: among candidates with equal coverage, pick the
   smallest threshold. Lower thresholds produce tighter, more granular clusters.

The "fewer non-outlier clusters" secondary criterion mentioned in the initial SPEC was
**not implemented** because it conflicts with the desired output for well-separated data
(see Context below).

## Status

Accepted.

## Context

The initial SPEC described a three-level tie-breaking rule:

> primary: non-outlier coverage  
> secondary: fewer non-outlier clusters (prefer simpler grouping when coverage is equal)  
> tertiary: lower threshold

The "fewer clusters" secondary pushes the algorithm to merge distinct groups when two
candidate thresholds achieve the same coverage. For a dataset with groups A (4 files),
B (4 files), and small (3 files < `min_cluster_size`):

- Threshold T₁ (between within-group merges and the A↔B merge): 3 clusters, coverage=8
- Threshold T₂ (between the A↔B merge and the A+B↔small merge): 2 clusters, coverage=8

With "fewer clusters" as secondary, T₂ wins — A and B are merged into one folder.
This is semantically wrong when A and B are genuinely distinct groups.

The contract test `test_agglomerative_tree_auto_k_routes_small_clusters_to_review`
encodes the correct expected behavior (A and B separate). Tests are authoritative per
the Definition of Done.

## Rationale

Omitting the "fewer clusters" secondary and going straight to "lower threshold" as
tiebreaker is consistent with the following intuition: if two thresholds cover the same
number of files, the tighter (lower) cut preserves finer structure that the similarity
data supports. Coarser merges are only preferred if they cover *more* files that would
otherwise be outliers — which is captured by the primary criterion.

## Consequences

- The `auto` strategy performs O(n) re-fits of `AgglomerativeClustering` (one per
  candidate threshold). For the MVP ceiling of ~200 files this is acceptable; revisit
  if inputs grow significantly.
- The SPEC section "How K Is Derived (Cutting The Tree)" is updated to match this rule.
- `clustering.cut_strategy` is reserved in config for future alternative strategies
  (e.g. `gap` for the simple largest-gap heuristic) but only `auto` is implemented.
