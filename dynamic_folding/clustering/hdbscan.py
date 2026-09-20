from __future__ import annotations

import numpy as np
import hdbscan as _hdbscan_pkg  # McInnes et al. package (pip install hdbscan)

from dynamic_folding.clustering.result import ClusterPartition, CondensedTreeData


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_children_of(
    parents: list[int],
    children: list[int],
) -> dict[int, list[int]]:
    """Build parent → [child, ...] adjacency from the condensed-tree lists."""
    adj: dict[int, list[int]] = {}
    for p, c in zip(parents, children):
        if p not in adj:
            adj[p] = []
        adj[p].append(c)
    return adj


def _get_leaves(node_id: int, children_of: dict[int, list[int]], n_leaves: int) -> list[int]:
    """Return all original data-point indices that are descendants of node_id."""
    if node_id < n_leaves:
        return [node_id]
    result: list[int] = []
    for child in children_of.get(node_id, []):
        result.extend(_get_leaves(child, children_of, n_leaves))
    return result


def _build_condensed_tree_data(
    hdb: object,  # fitted hdbscan.HDBSCAN instance
    n_leaves: int,
) -> CondensedTreeData:
    """Extract CondensedTreeData from a fitted McInnes HDBSCAN estimator."""
    ct_array = hdb.condensed_tree_.to_numpy()  # structured array

    parents = [int(r["parent"]) for r in ct_array]
    children_list = [int(r["child"]) for r in ct_array]
    lambda_vals = [float(r["lambda_val"]) for r in ct_array]
    child_sizes = [int(r["child_size"]) for r in ct_array]

    # Map top-level cluster labels → condensed-tree node ids (EOM-selected).
    # _select_clusters() is a stable semi-public method on CondensedTree that
    # returns the node ids chosen by the EOM or leaf criterion.
    selected_node_ids: list[int] = list(hdb.condensed_tree_._select_clusters())

    children_of = _build_children_of(parents, children_list)

    selected_nodes: dict[int, int] = {}
    for node_id in selected_node_ids:
        leaves = _get_leaves(node_id, children_of, n_leaves)
        for leaf in leaves:
            lab = int(hdb.labels_[leaf])
            if lab >= 0 and lab not in selected_nodes:
                selected_nodes[lab] = node_id
                break

    return CondensedTreeData(
        parents=parents,
        children=children_list,
        lambda_vals=lambda_vals,
        child_sizes=child_sizes,
        n_leaves=n_leaves,
        selected_nodes=selected_nodes,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cluster_hdbscan(
    vectors: list[list[float]],
    *,
    min_cluster_size: int = 5,
    min_samples: int | None = None,
    cluster_selection_epsilon: float = 0.0,
) -> ClusterPartition:
    """Cluster vectors with HDBSCAN (McInnes et al.) and capture the condensed tree.

    The returned ClusterPartition.linkage holds the full CondensedTreeData so that
    the proposer can extract sub-level folder structure by cutting the condensed tree
    with the EOM criterion — without re-running the algorithm on subsets.
    """
    if not vectors:
        return ClusterPartition(labels=[])

    if len(vectors) < min_cluster_size:
        # Not enough points to form even one cluster of min_size.
        return ClusterPartition(labels=[-1 for _ in vectors])

    X = np.asarray(vectors, dtype=float)
    hdb = _hdbscan_pkg.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_epsilon=cluster_selection_epsilon,
    )
    hdb.fit(X)

    labels = [int(x) for x in hdb.labels_.tolist()]
    ct_data = _build_condensed_tree_data(hdb, len(vectors))

    return ClusterPartition(labels=labels, linkage=ct_data)
