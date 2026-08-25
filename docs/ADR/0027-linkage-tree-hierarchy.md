# ADR 0027: Hierarchy from Linkage-Tree Cuts, Not Recursive Re-Clustering

Date: 2026-05-26

## Status

Accepted.

## Context

Before this ADR, `proposal/proposer.py::_build_level()` derived multi-level folder
proposals by calling the clustering algorithm **again** on each top-level cluster's
subset of vectors.  This recursive re-clustering approach contradicts both the
CLAUDE.md guidance ("the proposer derives multi-level folders by cutting the linkage
tree") and the theoretical argument made in the thesis (Cap. 2, Campello et al.
2013/2015), which identifies three problems with the stacked approach:

1. **Propagation of errors** – errors made at the top level are amplified at each
   deeper level.
2. **Structural inconsistency** – sub-level density estimates are computed on
   incomparable local subsets, not in the same global embedding space.
3. **Pipeline cost** – the algorithm is run O(K × depth) times instead of once.

## Decision

For algorithms that expose a complete hierarchical structure (`agglomerative_tree`
and `hdbscan`), the proposer now derives all levels by **cutting the same tree** that
was built during top-level clustering.

### agglomerative_tree

`sklearn.AgglomerativeClustering` is fitted with `compute_distances=True` to expose
`children_` (n−1 merge pairs) and `distances_` (n−1 merge distances).  These are
packaged as `AgglomerativeLinkage` inside `ClusterPartition.linkage`.

Sub-level extraction (`_cut_agglomerative_subtree`):
- Filters the linkage tree to merges whose **entire descendant set lies within the
  target subset of leaves**.
- Applies the same coverage-maximising / lower-threshold-tiebreaker heuristic as
  the top-level cut.
- Uses a union-find so no AgglomerativeClustering re-fit is needed.

### hdbscan

The McInnes et al. `hdbscan` package (added as a required dependency in place of
sklearn's `HDBSCAN`) exposes `condensed_tree_` after fitting.  The condensed tree
encodes the full hierarchical density structure.  It is stored as `CondensedTreeData`
inside `ClusterPartition.linkage`, along with a `selected_nodes` mapping that pairs
each top-level cluster label with its EOM-selected condensed-tree node id.

Sub-level extraction (`_hdbscan_eom_subtree`):
- Operates on the subtree rooted at the cluster's selected node.
- Applies the **EOM (Excess of Mass) criterion** within that subtree (Campello et al.
  2015, §3.3): stability = Σ child_sizes × (λ_split − λ_birth).
- The root of the subtree is **never selected** (we force at least one sub-division
  level), which is appropriate for folder-hierarchy proposals.
- A bottom-up stability propagation selects the optimal sub-clusters; nodes smaller
  than `min_cluster_size` are excluded.

### Fallback (kmeans / random_baseline)

Flat clusterers produce `ClusterPartition.linkage = None`.  The proposer detects this
and falls back to the previous `_build_level` re-clustering path unchanged.

## Consequences

- `ClusterPartition` is the new shared return type for all clusterers, replacing
  per-file `ClusterResult` dataclasses.  It holds `labels`, `linkage`, and
  `distance_threshold` (agglomerative telemetry).
- The `Clusterer` Protocol in `registries.py` now returns `ClusterPartition`.
  All existing callers that only need labels use `.labels`.
- `hdbscan>=0.8.38` is a **required** dependency (not optional).  Without it the
  `hdbscan` clustering provider does not function.
- Sub-level extraction is now `O(n)` per level (union-find / tree walk) rather than
  re-running a full clustering algorithm.
- All three arguments in the thesis for tree-based hierarchy extraction now match the
  actual implementation.

## Related

- ADR 0004: original agglomerative tree decision.
- ADR 0006: HDBSCAN introduction.
- ADR 0010 / ADR 0016: earlier recursive-subdivision decisions (superseded for
  agglomerative_tree and hdbscan by this ADR).
